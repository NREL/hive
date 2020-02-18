from __future__ import annotations

import csv
from datetime import datetime
import functools as ft
import os
from typing import Tuple, Dict

import immutables
from hive.reporting import DetailedReporter
from pkg_resources import resource_filename

from hive.config import HiveConfig
from hive.model.base import Base
from hive.model.energy.powercurve import build_powercurve
from hive.model.energy.powertrain import build_powertrain
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.osm_roadnetwork import OSMRoadNetwork
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.util.helpers import DictOps


def initialize_simulation(
        config: HiveConfig
) -> Tuple[SimulationState, Environment]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network

    :param config: the configuration of this run
    :return: a SimulationState, or a SimulationStateError
    :raises Exception due to IOErrors, missing keys in DictReader rows, or parsing errors
    """

    vehicles_file = resource_filename("hive.resources.vehicles", config.io.vehicles_file)
    bases_file = resource_filename("hive.resources.bases", config.io.bases_file)
    stations_file = resource_filename("hive.resources.stations", config.io.stations_file)

    run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    sim_output_dir = os.path.join(config.io.working_directory, run_name)
    if not os.path.isdir(sim_output_dir):
        os.makedirs(sim_output_dir)

    if config.io.geofence_file:
        geofence_file = resource_filename("hive.resources.geofence", config.io.geofence_file)
        geofence = GeoFence.from_geojson_file(geofence_file)
    else:
        geofence = None

    if not config.io.road_network_file:
        road_network = HaversineRoadNetwork(geofence=geofence, sim_h3_resolution=config.sim.sim_h3_resolution)
    else:
        road_network_file = resource_filename("hive.resources.road_network", config.io.road_network_file)
        road_network = OSMRoadNetwork(
            geofence=geofence,
            sim_h3_resolution=config.sim.sim_h3_resolution,
            road_network_file=road_network_file,
        )

    sim_initial = SimulationState(
        road_network=road_network,
        sim_time=config.sim.start_time,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_location_resolution=config.sim.sim_h3_resolution,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution
    )

    reporter = DetailedReporter(config.io, sim_output_dir)
    env_initial = Environment(config=config, reporter=reporter)

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
        veh = Vehicle.from_row(row, sim.road_network)
        updated_sim = sim.add_vehicle(veh)

        if isinstance(updated_sim, Exception):
            raise updated_sim
        else:
            if row['powertrain_id'] not in env.powertrains and row['powercurve_id'] not in env.powercurves:
                powertrain = build_powertrain(row['powertrain_id'])
                powercurve = build_powercurve(row['powercurve_id'])
                updated_env = env.add_powercurve(powercurve).add_powertrain(powertrain)
                return updated_sim, updated_env
            elif row['powertrain_id'] not in env.powertrains:
                powertrain = build_powertrain(row['powertrain_id'])
                updated_env = env.add_powertrain(powertrain)
                return updated_sim, updated_env
            elif row['powercurve_id'] not in env.powercurves:
                powercurve = build_powercurve(row['powercurve_id'])
                updated_env = env.add_powercurve(powercurve)
                return updated_sim, updated_env
            else:
                return updated_sim, env

    # open vehicles file and add each row
    with open(vehicles_file, 'r', encoding='utf-8-sig') as vf:
        reader = csv.DictReader(vf)
        initial_payload = simulation_state, environment
        sim_with_vehicles = ft.reduce(_add_row_unsafe, reader, initial_payload)

    return sim_with_vehicles


def _build_bases(bases_file: str, simulation_state: SimulationState) -> SimulationState:
    """
    all your base are belong to us

    :param bases_file: path to file with bases
    :param simulation_state: the partial simulation state
    :return: the simulation state with all bases in it
    :raises Exception if a parse error in Base.from_row or any error adding the Base to the Sim
    """

    def _add_row_unsafe(sim: SimulationState, row: Dict[str, str]) -> SimulationState:
        base = Base.from_row(row, simulation_state.road_network)
        updated_sim = sim.add_base(base)
        if isinstance(updated_sim, Exception):
            raise updated_sim
        else:
            return updated_sim

    # add all bases from the base file
    with open(bases_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        sim_with_bases = ft.reduce(_add_row_unsafe, reader, simulation_state)

    return sim_with_bases


def _build_stations(stations_file: str, simulation_state: SimulationState) -> SimulationState:
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
        sim_with_station = sim.add_station(station)
        if isinstance(sim_with_station, Exception):
            raise sim_with_station
        else:
            return sim_with_station

    # grab all stations (some may exist on multiple rows)
    with open(stations_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        stations_builder = ft.reduce(_add_row_unsafe, reader, immutables.Map())

    # add all stations to the simulation once we know they are complete
    sim_with_stations = ft.reduce(_add_station_unsafe, stations_builder.values(), simulation_state)

    return sim_with_stations
