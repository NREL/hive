from __future__ import annotations

import csv
import functools as ft
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional, Callable

import immutables
from returns.primitives.exceptions import UnwrapFailedError

from hive import Update, StepSimulation
from hive.config import HiveConfig
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.initialization.sample_vehicles import (
    sample_vehicles,
    build_default_location_sampling_fn,
    build_default_soc_sampling_fn,
)
from hive.model.base import Base
from hive.model.energy.charger import build_chargers_table
from hive.model.request import Request
from hive.model.roadnetwork import Link
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.osm_roadnetwork import OSMRoadNetwork
from hive.model.station import Station
from hive.model.vehicle.mechatronics import build_mechatronics_table
from hive.model.vehicle.schedules import build_schedules_table
from hive.reporting.handler.eventful_handler import EventfulHandler
from hive.reporting.handler.instruction_handler import InstructionHandler
from hive.reporting.handler.stateful_handler import StatefulHandler
from hive.reporting.handler.stats_handler import StatsHandler
from hive.reporting.reporter import Reporter
from hive.runner import RunnerPayload
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.cancel_requests import CancelRequests
from hive.state.simulation_state.update.charging_price_update import ChargingPriceUpdate
from hive.state.simulation_state.update.update_requests_sampling import UpdateRequestsSampling
from hive.util import DictOps, Ratio

log = logging.getLogger(__name__)


def initialize_simulation_with_sampling(
        config: HiveConfig,
        vehicle_count: int,
        instruction_generators: Tuple[InstructionGenerator, ...],
        vehicle_location_sampling_function: Optional[Callable[[], Link]] = None,
        vehicle_soc_sampling_function: Optional[Callable[[], Ratio]] = None,
        request_sampling_function: Optional[Callable[[SimulationState], Tuple[Request, ...]]] = None,
) -> RunnerPayload:
    """
    constructs a RunnerPayload, ready to simulate.
    uses sampling functions to build vehicles and requests

    :param config: the configuration of this run
    :param vehicle_count: how many vehicles to initialize
    :param instruction_generators: which instruction generators to use
    :param vehicle_location_sampling_function: an optional location sampling function; uses default if none
    :param vehicle_soc_sampling_function: an optional vehicle soc sampling function; uses default if none
    :param request_sampling_function: an optional request sampling function; uses default if none

    :return: a RunnerPayload
    :raises Exception due to IOErrors, missing keys in DictReader rows, or parsing errors
    """

    # deprecated geofence input
    if config.input_config.geofence_file:
        geofence = GeoFence.from_geojson_file(config.input_config.geofence_file)
    else:
        geofence = None

    # set up road network based on user-configured road network type
    if config.network.network_type == 'euclidean':
        road_network = HaversineRoadNetwork(geofence=geofence, sim_h3_resolution=config.sim.sim_h3_resolution)
    elif config.network.network_type == 'osm_network':
        road_network = OSMRoadNetwork(
            geofence=geofence,
            sim_h3_resolution=config.sim.sim_h3_resolution,
            road_network_file=Path(config.input_config.road_network_file),
            default_speed_kmph=config.network.default_speed_kmph,
        )
    else:
        raise IOError(
            f"road network type {config.network.network_type} not valid, must be one of {{euclidean|osm_network}}")

    # initial sim state with road network and no entities
    sim_initial = SimulationState(
        road_network=road_network,
        sim_time=config.sim.start_time,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_location_resolution=config.sim.sim_h3_resolution,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution
    )

    # configure reporting
    reporter = Reporter(config.global_config)
    if config.global_config.log_events:
        reporter.add_handler(EventfulHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_states:
        reporter.add_handler(StatefulHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_instructions:
        reporter.add_handler(InstructionHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_stats:
        reporter.add_handler(StatsHandler())

    # create simulation environment
    if config.input_config.fleets_file:
        log.warning("the simulation is using sampling which doesn't support a fleet file input;\n"
                    "this input will be ignored and entities will not have any fleet information.")

    env = Environment(config=config,
                              reporter=reporter,
                              mechatronics=build_mechatronics_table(config.input_config.mechatronics_file,
                                                                    config.input_config.scenario_directory),
                              chargers=build_chargers_table(config.input_config.chargers_file),
                              schedules=build_schedules_table(config.sim.schedule_type,
                                                              config.input_config.schedules_file),
                              )

    # populate simulation with static entities
    sim_with_bases = _build_bases(config.input_config.bases_file, sim_initial)
    sim_with_stations = _build_stations(config.input_config.stations_file, sim_with_bases)

    # sample vehicles
    if not vehicle_location_sampling_function:
        vehicle_location_sampling_function = build_default_location_sampling_fn()
    if not vehicle_soc_sampling_function:
        vehicle_soc_sampling_function = build_default_soc_sampling_fn()

    sample_result = sample_vehicles(
        count=vehicle_count,
        sim=sim_with_stations,
        env=env,
        location_sampling_function=vehicle_location_sampling_function,
        soc_sampling_function=vehicle_soc_sampling_function,
    )

    try:
        sim_w_vehicles = sample_result.unwrap()
    except UnwrapFailedError:
        raise Exception(sample_result._inner_value.args[0])

    if request_sampling_function is None:
        update_requests = UpdateRequestsSampling.build(rate_structure_file=config.input_config.rate_structure_file)
    else:
        update_requests = UpdateRequestsSampling.build(
            rate_structure_file=config.input_config.rate_structure_file,
            sampling_function=request_sampling_function,
        )

    update = Update(
        pre_step_update=(
            ChargingPriceUpdate.build(
                config.input_config.charging_price_file,
                config.input_config.chargers_file,
                lazy_file_reading=config.global_config.lazy_file_reading,
            ),
            update_requests,
            CancelRequests(),
        ),
        step_update=StepSimulation(instruction_generators)
    )

    return RunnerPayload(sim_w_vehicles, env, update)


def _build_bases(bases_file: str,
                 simulation_state: SimulationState,
                 ) -> SimulationState:
    """
    all your base are belong to us

    :param bases_file: path to file with bases
    :param simulation_state: the partial simulation state
    :return: the simulation state with all bases in it
    :raises Exception if a parse error in Base.from_row or any error adding the Base to the Sim
    """

    def _add_row_unsafe(sim: SimulationState, row: Dict[str, str]) -> SimulationState:
        base = Base.from_row(row, simulation_state.road_network)
        error, updated_sim = simulation_state_ops.add_base(sim, base)
        if error:
            log.error(error)
            return sim
        else:
            return updated_sim

    # add all bases from the base file
    with open(bases_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        sim_with_bases = ft.reduce(_add_row_unsafe, reader, simulation_state)

    return sim_with_bases


def _build_stations(stations_file: str,
                    simulation_state: SimulationState,
                    ) -> SimulationState:
    """
    all your station are belong to us

    :param stations_file: the file with stations in it
    :param simulation_state: the partial simulation state
    :return: the resulting simulation state with all stations in it
    :raises Exception if parsing a Station row failed or adding a Station to the Simulation failed
    """

    def _add_row_unsafe(builder: immutables.Map[str, Station], row: Dict[str, str]) -> immutables.Map[str, Station]:
        station = Station.from_row(row, builder, simulation_state.road_network)
        updated_builder = DictOps.add_to_dict(builder, station.id, station)
        return updated_builder

    def _add_station_unsafe(sim: SimulationState, station: Station) -> SimulationState:
        error, sim_with_station = simulation_state_ops.add_station(sim, station)
        if error:
            log.error(error)
            return sim
        else:
            return sim_with_station

    # grab all stations (some may exist on multiple rows)
    with open(stations_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        stations_builder = ft.reduce(_add_row_unsafe, reader, immutables.Map())

    # add all stations to the simulation once we know they are complete
    sim_with_stations = ft.reduce(_add_station_unsafe, stations_builder.values(), simulation_state)

    return sim_with_stations
