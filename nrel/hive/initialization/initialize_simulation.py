from __future__ import annotations

import os
import csv
import functools as ft
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Tuple, Dict

import immutables

from nrel.hive.config import HiveConfig
from nrel.hive.initialization.initialize_ops import (
    process_fleet_file,
    read_fleet_ids_from_file,
)
from nrel.hive.model.base import Base
from nrel.hive.model.energy.charger import build_chargers_table
from nrel.hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork
from nrel.hive.model.station.station import Station
from nrel.hive.model.vehicle.mechatronics import build_mechatronics_table
from nrel.hive.model.vehicle.schedules import build_schedules_table
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.reporting.handler.eventful_handler import EventfulHandler
from nrel.hive.reporting.handler.instruction_handler import InstructionHandler
from nrel.hive.reporting.handler.kepler_handler import KeplerHandler
from nrel.hive.reporting.handler.stateful_handler import StatefulHandler
from nrel.hive.reporting.handler.stats_handler import StatsHandler
from nrel.hive.reporting.handler.time_step_stats_handler import TimeStepStatsHandler
from nrel.hive.reporting.reporter import Reporter
from nrel.hive.runner.environment import Environment
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.util.dict_ops import DictOps

if TYPE_CHECKING:
    from nrel.hive.util.typealiases import ScheduleId
    from nrel.hive.model.vehicle.schedules import ScheduleFunction

log = logging.getLogger(__name__)

# All initialization functions must adhere to the following type signature.
# These functions are called to initialize the simulation state and the environment
# and are abstracted such that an external init function can be added to enable custom
# initialization.
InitFunction = Callable[
    [HiveConfig, SimulationState, Environment], Tuple[SimulationState, Environment]
]


def initialize(
    config: HiveConfig, init_functions: Optional[Iterable[InitFunction]] = None
) -> Tuple[SimulationState, Environment]:
    """
    Initialize a simulation using a config object and a set of arbitrary initialization functions.
    If no initialziation functions are specified, we use a set of default functions to provide basic initialization

    NOTE: If providing custom initialization functions, the default functions would be overritten
    and so be sure to also include the default functions when passing any functions via the init_functions
    parameter.

    ALSO NOTE: The order of the initialization matters as some initialization functions depend on a previous
    function. For example, the base, station and vehicle initialization functions need to have access to the
    road network and so that initalization step must come before those functions are called.

    :param config: the configuration of this run
    :param init_functions: any optional custom initialization functions

    :return: an initialized SimulationState and Environment
    :raises Exception due to IOErrors, missing keys in DictReader rows, or parsing errors
    """
    if init_functions is None:
        init_functions = default_init_functions()

    sim = SimulationState(
        sim_time=config.sim.start_time,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_location_resolution=config.sim.sim_h3_resolution,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution,
    )

    environment = Environment(config=config)

    for init_function in init_functions:
        sim, environment = init_function(config, sim, environment)

    return sim, environment


def initialize_environment_fleets(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    An initialization function to add fleets to the environment

    :param config: the configuration of this run
    :param simulation_state: the partially initialized simulation state
    :param environment: the partially initialized environment

    :return: a SimulationState and Environment with fleets added
    """
    fleet_ids = (
        read_fleet_ids_from_file(config.input_config.fleets_file)
        if config.input_config.fleets_file
        else frozenset()
    )

    environment = environment._replace(fleet_ids=fleet_ids)

    return simulation_state, environment


def initialize_environment_schedules(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    An initialization function to add schedules to the environment

    :param config: the configuration of this run
    :param simulation_state: the partially initialized simulation state
    :param environment: the partially initialized environment

    :return: a SimulationState and Environment with schedules added
    """

    if config.input_config.schedules_file is None:
        schedules: immutables.Map[ScheduleId, ScheduleFunction] = immutables.Map()
    else:
        schedules = build_schedules_table(
            config.sim.schedule_type, config.input_config.schedules_file
        )

    environment = environment._replace(schedules=schedules)

    return simulation_state, environment


def initialize_environment_mechatronics(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    An initialization function to add mechatronics to the environment

    :param config: the configuration of this run
    :param simulation_state: the partially initialized simulation state
    :param environment: the partially initialized environment

    :return: a SimulationState and Environment with mechatronics added
    """
    mechatronics_table = build_mechatronics_table(
        config.input_config.mechatronics_file, config.input_config.scenario_directory
    )
    environment = environment._replace(mechatronics=mechatronics_table)

    return simulation_state, environment


def initialize_environment_chargers(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    An initialization function to add chargers to the environment

    :param config: the configuration of this run
    :param simulation_state: the partially initialized simulation state
    :param environment: the partially initialized environment

    :return: a SimulationState and Environment with chargers added
    """
    chargers_table = build_chargers_table(config.input_config.chargers_file)
    environment = environment._replace(chargers=chargers_table)

    return simulation_state, environment


def initialize_environment_reporting(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    An initialization function to add reporting to the environment

    :param config: the configuration of this run
    :param simulation_state: the partially initialized simulation state
    :param environment: the partially initialized environment

    :return: a SimulationState and Environment with reporting added
    """
    # configure reporting
    reporter = Reporter()
    if config.global_config.log_events:
        reporter.add_handler(
            EventfulHandler(config.global_config, config.scenario_output_directory)
        )
    if config.global_config.log_states:
        reporter.add_handler(
            StatefulHandler(config.global_config, config.scenario_output_directory)
        )
    if config.global_config.log_instructions:
        reporter.add_handler(
            InstructionHandler(config.global_config, config.scenario_output_directory)
        )
    if config.global_config.log_kepler:
        reporter.add_handler(KeplerHandler(config.scenario_output_directory))
    if config.global_config.log_stats:
        reporter.add_handler(StatsHandler())
    if config.global_config.log_time_step_stats or config.global_config.log_fleet_time_step_stats:
        reporter.add_handler(
            TimeStepStatsHandler(config, config.scenario_output_directory, environment.fleet_ids)
        )

    environment = environment.set_reporter(reporter)

    return simulation_state, environment


def default_init_functions() -> Iterable[InitFunction]:
    """
    Returns the defaul initialization functions in the proper order.
    """
    return [
        initialize_environment_fleets,
        initialize_environment_schedules,
        initialize_environment_mechatronics,
        initialize_environment_chargers,
        initialize_environment_reporting,
        vehicle_init_function,
        station_init_function,
        base_init_function,
    ]


def osm_init_function(
    config: HiveConfig,
    simulation_state: SimulationState,
    environment: Environment,
    cache_dir=Path.home(),
) -> Tuple[SimulationState, Environment]:
    """
    Initialize an OSMRoadNetwork and add to the simulation

    :param config: the hive config
    :param simulation_state: the partially-constructed simulation state
    :param environment: the partially-constructed environment

    :return: the SimulationState with the OSMRoadNetwork in it

    :raises Exception: from IOErrors parsing the road network
    """

    if config.input_config.road_network_file:
        road_network = OSMRoadNetwork.from_file(
            sim_h3_resolution=config.sim.sim_h3_resolution,
            road_network_file=config.input_config.road_network_file,
            default_speed_kmph=config.network.default_speed_kmph,
        )
    elif config.input_config.geofence_file:
        try:
            import geopandas
        except ImportError as e:
            raise ImportError(
                "Must have geopandas installed if you want to load from geofence file"
            ) from e

        dataframe = geopandas.read_file(config.input_config.geofence_file)
        polygon_union = dataframe["geometry"].unary_union

        road_network = OSMRoadNetwork.from_polygon(
            sim_h3_resolution=config.sim.sim_h3_resolution,
            default_speed_kmph=config.network.default_speed_kmph,
            polygon=polygon_union,
            cache_dir=cache_dir,
        )
    else:
        raise IOError(
            "Must supply either a road network or geofence file when using the osm_network"
        )

    sim_w_osm = simulation_state._replace(road_network=road_network)

    return sim_w_osm, environment


def vehicle_init_function(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    adds all vehicles from the provided vehicles file

    :param config: the hive config
    :param simulation_state: the partially-constructed simulation state
    :param environment: the partially-constructed environment

    :return: the SimulationState with vehicles in it
    :raises Exception: from IOErrors parsing the vehicle, powertrain, or powercurve files
    """
    vehicles_file = config.input_config.vehicles_file
    vehicle_member_ids = (
        process_fleet_file(config.input_config.fleets_file, "vehicles")
        if config.input_config.fleets_file
        else None
    )

    def _collect_vehicle(row: Dict[str, str]) -> Optional[Vehicle]:
        veh = Vehicle.from_row(row, simulation_state.road_network, environment)

        if vehicle_member_ids is not None:
            if veh.id in vehicle_member_ids:
                veh = veh.set_membership(vehicle_member_ids[veh.id])

        return veh

    # open vehicles file and add each row
    with open(vehicles_file, "r", encoding="utf-8-sig") as vf:
        reader = csv.DictReader(vf)
        vehicles_or_none = [_collect_vehicle(row) for row in reader]
        vehicles = [v for v in vehicles_or_none if v is not None]
        sim_with_vehicles = simulation_state_ops.add_entities(simulation_state, vehicles)

    return sim_with_vehicles, environment


def base_init_function(
    config: HiveConfig, simulation_state: SimulationState, environment: Environment
) -> Tuple[SimulationState, Environment]:
    """
    all your base are belong to us

    :param bases_file: path to file with bases
    :param base_member_ids: an immutables Map with all of the base membership ids
    :param simulation_state: the partial simulation state
    :param base_filter: a function that returns True if a base should be filtered out of the simulation

    :return: the simulation state with all bases in it
    :raises Exception if a parse error in Base.from_row or any error adding the Base to the Sim
    """
    base_member_ids = (
        process_fleet_file(config.input_config.fleets_file, "bases")
        if config.input_config.fleets_file
        else None
    )

    def _collect_base(row: Dict[str, str]) -> Optional[Base]:
        base = Base.from_row(row, simulation_state.road_network)

        if base_member_ids is not None:
            if base.id in base_member_ids:
                base = base.set_membership(base_member_ids[base.id])
        return base

    # add all bases from the base file
    with open(config.input_config.bases_file, "r", encoding="utf-8-sig") as bf:
        reader = csv.DictReader(bf)
        bases_or_none = [_collect_base(row) for row in reader]
        bases = [b for b in bases_or_none if b is not None]

    sim_w_bases = simulation_state_ops.add_entities(simulation_state, bases)

    sim_w_home_bases = _assign_private_memberships(sim_w_bases)

    return sim_w_home_bases, environment


def _assign_private_memberships(sim: SimulationState) -> SimulationState:
    """
    vehicles which had a home base assigned will automatically generate a home base membership id
    which links the vehicle and the base, in order to avoid having to specify this (obvious) relationship
    in the fleets configuration of a scenario.

    :param sim: partial simulation state with vehicles and bases added
    :return: sim state where vehicles + bases which should have a private relationship have been updated
    """

    def _find_human_drivers(acc: SimulationState, v: Vehicle) -> SimulationState:
        home_base_id = v.driver_state.home_base_id
        if home_base_id is None:
            return acc
        else:
            home_base = sim.bases.get(home_base_id)
            if not home_base:
                log.error(
                    f"home base {home_base_id} does not exist but is listed as home base for vehicle {v.id}"
                )
                return acc
            else:
                home_base_membership_id = f"{v.id}_private_{home_base_id}"
                updated_v = v.add_membership(home_base_membership_id)
                updated_b = home_base.add_membership(home_base_membership_id)

                error_v, with_v = simulation_state_ops.modify_vehicle(acc, updated_v)
                if error_v:
                    log.error(error_v)
                    return acc
                elif with_v is None:
                    return acc
                else:
                    error_b, with_b = simulation_state_ops.modify_base(with_v, updated_b)
                    if error_b:
                        log.error(error_b)
                        return acc
                    elif with_b is None:
                        return acc
                    else:
                        if home_base.station_id is None:
                            return with_b
                        else:
                            station = sim.stations.get(home_base.station_id)
                            if station is None:
                                return with_b
                            updated_s = station.add_membership(home_base_membership_id)
                            (
                                error_s,
                                with_s,
                            ) = simulation_state_ops.modify_station(with_b, updated_s)
                            if error_s:
                                log.error(error_s)
                                return acc
                            elif with_s is None:
                                return acc
                            else:
                                return with_s

    result = ft.reduce(_find_human_drivers, sim.get_vehicles(), sim)
    return result


def station_init_function(
    config: HiveConfig,
    simulation_state: SimulationState,
    environment: Environment,
) -> Tuple[SimulationState, Environment]:
    """
    all your station are belong to us

    :param config: the hive config
    :param simulation_state: the partial simulation state
    :param environment: the simulation environment

    :return: the resulting simulation state with all stations in it
    :raises Exception if parsing a Station row failed or adding a Station to the Simulation failed
    """
    station_member_ids = (
        process_fleet_file(config.input_config.fleets_file, "stations")
        if config.input_config.fleets_file
        else None
    )

    def _add_row_unsafe(
        builder: immutables.Map[str, Station], row: Dict[str, str]
    ) -> immutables.Map[str, Station]:
        station = Station.from_row(row, builder, simulation_state.road_network, environment)

        if station_member_ids is not None:
            if station.id in station_member_ids:
                station = station.set_membership(station_member_ids[station.id])

        updated_builder = DictOps.add_to_dict(builder, station.id, station)
        return updated_builder

    # grab all stations (some may exist on multiple rows)
    with open(config.input_config.stations_file, "r", encoding="utf-8-sig") as bf:
        reader = csv.DictReader(bf)
        stations_builder: immutables.Map[str, Station] = ft.reduce(
            _add_row_unsafe, reader, immutables.Map()
        )

    # add all stations to the simulation once we know they are complete
    return (
        simulation_state_ops.add_entities(simulation_state, stations_builder.values()),
        environment,
    )
