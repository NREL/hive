from __future__ import annotations

import csv
import functools as ft
import logging
from typing import Tuple, Dict

import immutables

from hive.config import HiveConfig
from hive.model.base import Base
from hive.model.energy.charger import build_chargers_table
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.osm_roadnetwork import OSMRoadNetwork
from hive.model.station import Station
from hive.model.vehicle.mechatronics import build_mechatronics_table
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.reporter import Reporter
from hive.reporting.sim_log_handler import SimLogHandler
from hive.reporting.stats_handler import StatsHandler
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util.helpers import DictOps

log = logging.getLogger(__name__)


def initialize_simulation(
        config: HiveConfig,
) -> Tuple[SimulationState, Environment]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network

    :param config: the configuration of this run
    :return: a SimulationState, or a SimulationStateError
    :raises Exception due to IOErrors, missing keys in DictReader rows, or parsing errors
    """

    vehicles_file = config.input_config.vehicles_file
    bases_file = config.input_config.bases_file
    stations_file = config.input_config.stations_file

    if config.input_config.geofence_file:
        geofence = GeoFence.from_geojson_file(config.input_config.geofence_file)
    else:
        geofence = None

    if config.network.network_type == 'euclidean':
        road_network = HaversineRoadNetwork(geofence=geofence, sim_h3_resolution=config.sim.sim_h3_resolution)
    elif config.network.network_type == 'osm_network':
        road_network = OSMRoadNetwork(
            geofence=geofence,
            sim_h3_resolution=config.sim.sim_h3_resolution,
            road_network_file=config.input_config.road_network_file,
            default_speed_kmph=config.network.default_speed_kmph,
        )
    else:
        raise IOError(f"road network type {config.network.network_type} not valid, must be one of {{euclidean|osm_network}}")

    sim_initial = SimulationState(
        road_network=road_network,
        sim_time=config.sim.start_time,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_location_resolution=config.sim.sim_h3_resolution,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution
    )

    if config.global_config.log_period_seconds < config.sim.timestep_duration_seconds:
        raise RuntimeError("log time step must be greater than simulation time step")

    reporter = Reporter(config.global_config)

    if config.global_config.log_sim:
        reporter.add_handler(SimLogHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.track_stats:
        reporter.add_handler(StatsHandler())

    env_initial = Environment(config=config,
                              reporter=reporter,
                              mechatronics=build_mechatronics_table(config.input_config),
                              chargers=build_chargers_table(config.input_config.chargers_file)
                              )

    # todo: maybe instead of reporting errors to the env.Reporter in these builder functions, we
    #  should instead hold aside any error reports and then do something below after finishing,
    #  such as allowing the user to decide how to respond (via a config param such as "fail on load errors")
    # this way, they get to see all of the errors at once instead of having to fail, fix, and reload constantly :-)
    sim_with_vehicles, env_updated = _build_vehicles(vehicles_file, sim_initial, env_initial)
    sim_with_bases = _build_bases(bases_file, sim_with_vehicles)
    sim_with_stations = _build_stations(stations_file, sim_with_bases)

    return sim_with_stations, env_updated


def _build_vehicles(
        vehicles_file: str,
        simulation_state: SimulationState,
        environment: Environment) -> Tuple[SimulationState, Environment]:
    """
    adds all vehicles from the provided vehicles file

    :param vehicles_file: the file to load vehicles from
    :param simulation_state: the partially-constructed simulation state
    :param environment: the partially-constructed environment
    :return: the SimulationState with vehicles in it
    :raises Exception: from IOErrors parsing the vehicle, powertrain, or powercurve files
    """

    def _add_row_unsafe(
            payload: Tuple[SimulationState, Environment],
            row: Dict[str, str]) -> Tuple[SimulationState, Environment]:

        sim, env = payload
        veh = Vehicle.from_row(row, sim.road_network, env)
        error, updated_sim = simulation_state_ops.add_vehicle(sim, veh)
        if error:
            log.error(error)
            return sim, env
        else:
            return updated_sim, env

    # open vehicles file and add each row
    with open(vehicles_file, 'r', encoding='utf-8-sig') as vf:
        reader = csv.DictReader(vf)
        initial_payload = simulation_state, environment
        sim_with_vehicles = ft.reduce(_add_row_unsafe, reader, initial_payload)

    return sim_with_vehicles


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