from __future__ import annotations

import functools as ft
from typing import Union, Tuple, cast

from hive.config import HiveConfig, IO, Sim
from hive.model.base import Base
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.state.simulation_state import SimulationState
from hive.util.exception import *
from hive.util.typealiases import SimTime
from hive.util.units import Seconds


def initial_simulation_state(
        io: IO,
        sim: Sim,
        start_time: SimTime = 0,
        sim_timestep_duration_seconds: Seconds = 1,
        sim_h3_location_resolution: int = 15,
        sim_h3_search_resolution: int = 7,
) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network

    :param io: the configuration used to load the files related to this SimulationState
    :param sim: the
    :param start_time: the start time for this simulation (by default, time step 0)
    :param sim_timestep_duration_seconds: the size of a time step in seconds
    :param sim_h3_location_resolution: the h3 resolution for internal positioning (comparison ops can override)
    :param sim_h3_search_resolution: the h3 upper-resolution for the bi-level location search
    :return: a SimulationState, or a SimulationStateError
    """

    vehicles_file = os.path.join(RESOURCES, 'vehicles', io.vehicles_file)
    requests_file = os.path.join(RESOURCES, 'requests', io.requests_file)
    bases_file = os.path.join(RESOURCES, 'bases', io.bases_file)
    stations_file = os.path.join(RESOURCES, 'stations', io.stations_file)

    road_network = HaversineRoadNetwork(sim_h3_location_resolution)

    build_errors = []

    with open(vehicles_file, 'r', encoding='utf-8-sig') as vf:
        builder = []
        reader = csv.DictReader(vf)
        for row in reader:
            try:
                vehicle = Vehicle.from_row(row, road_network)
                builder.append(vehicle)
            except IOError as err:
                build_errors.append(err)
            try:
                if row['powertrain_id'] not in env.powertrains:
                    powertrain = build_powertrain(row['powertrain_id'])
                    env = env.add_powertrain(powertrain)
            except IOError as err:
                build_errors.append(err)
            try:
                if row['powercurve_id'] not in env.powercurves:
                    powercurve = build_powercurve(row['powercurve_id'])
                    env = env.add_powercurve(powercurve)
            except IOError as err:
                build_errors.append(err)

        vehicles = tuple(builder)

    with open(bases_file, 'r', encoding='utf-8-sig') as bf:
        builder = []
        reader = csv.DictReader(bf)
        for row in reader:
            try:
                base = Base.from_row(row, config.sim.sim_h3_resolution)
                builder.append(base)
            except IOError as err:
                build_errors.append(err)

        bases = tuple(builder)

    with open(stations_file, 'r', encoding='utf-8-sig') as sf:
        builder = {}
        reader = csv.DictReader(sf)
        for row in reader:
            try:
                station = Station.from_row(row, builder, config.sim.sim_h3_resolution)
                builder[station.id] = station
            except IOError as err:
                build_errors.append(err)

        stations = tuple(builder.values())

    if build_errors:
        raise Exception(build_errors)

    initial_sim, sim_state_errors = initial_simulation_state(
        road_network=road_network,
        vehicles=vehicles,
        stations=stations,
        bases=bases,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution,
    )

    if sim_state_errors:
        raise Exception(sim_state_errors)

    # copy in fields which do not require additional work
    simulation_state_builder = SimulationState(
        road_network=road_network,
        initial_sim_time=start_time,
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_location_resolution=sim_h3_location_resolution,
        sim_h3_search_resolution=sim_h3_search_resolution
    )
    failures: Tuple[SimulationStateError, ...] = tuple()

    # add vehicles, stations, bases
    has_vehicles = ft.reduce(
        _add_to_builder,
        vehicles,
        (simulation_state_builder, failures)
    )
    has_vehicles_and_stations = ft.reduce(
        _add_to_builder,
        stations,
        has_vehicles
    )
    has_bases = ft.reduce(
        _add_to_builder,
        bases,
        has_vehicles_and_stations
    )

    return has_bases


def _add_to_builder(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
                    x: Union[Vehicle, Station, Base]) \
        -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
    """
    adds a single Vehicle, Station, Base, Powertrain, or Powercurve to the simulator, unless it is invalid

    :param acc: the partially-constructed SimulationState
    :param x: a new Vehicle, Station, or Base
    :return: add x, or, if it failed, update our log of failures
    """
    # unpack accumulator
    this_simulation_state: SimulationState = acc[0]
    this_failures: Tuple[SimulationStateError, ...] = acc[1]

    # add a Vehicle
    if isinstance(x, Vehicle):
        vehicle = cast(Vehicle, x)
        result = this_simulation_state.add_vehicle(vehicle)
        if isinstance(result, SimulationStateError):
            return this_simulation_state, (result,) + this_failures
        else:
            return result, this_failures

    # add a Station
    elif isinstance(x, Station):
        station = cast(Station, x)
        result = this_simulation_state.add_station(station)
        if isinstance(result, SimulationStateError):
            return this_simulation_state, (result,) + this_failures
        else:
            return result, this_failures

    # add a Base
    elif isinstance(x, Base):
        base = cast(Base, x)
        result = this_simulation_state.add_base(base)
        if isinstance(result, SimulationStateError):
            return this_simulation_state, (result,) + this_failures
        else:
            return result, this_failures

    else:
        # x is something else; do not modify simulation
        failure = SimulationStateError(f"not a Vehicle, Station, or Base: {x}")
        return this_simulation_state, (failure,) + this_failures
