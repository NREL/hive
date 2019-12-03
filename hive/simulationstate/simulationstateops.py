from __future__ import annotations

import functools as ft
from typing import Optional, Union, Tuple, cast

from hive.model.base import Base
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.simulationstate.simulationstate import SimulationState
from hive.util.exception import *
from hive.util.typealiases import Time


def initial_simulation_state(
        road_network: RoadNetwork,
        vehicles: Tuple[Vehicle, ...] = (),
        stations: Tuple[Station, ...] = (),
        bases: Tuple[Base, ...] = (),
        start_time: int = 0,
        sim_timestep_duration_seconds: Time = 1,
        sim_h3_resolution: int = 15
) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network
    :param road_network: the (initial) road network
    :param vehicles: the vehicles available in this simulation
    :param stations: the stations available in this simulation
    :param bases: the bases available in this simulation
    :param start_time: the start time for this simulation (by default, time step 0)
    :param sim_timestep_duration_seconds: the size of a time step in seconds
    :param sim_h3_resolution: the h3 resolution for internal positioning (comparison ops can override)
    :return: a SimulationState, or a SimulationStateError
    """

    # copy in fields which do not require additional work
    simulation_state_builder = SimulationState(
        road_network=road_network,
        sim_time=start_time,
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_resolution=sim_h3_resolution)
    failures: Tuple[SimulationStateError, ...] = tuple()

    # add vehicles, stations, and bases
    has_vehicles = ft.reduce(
        _add_to_accumulator,
        vehicles,
        (simulation_state_builder, failures)
    )
    has_vehicles_and_stations = ft.reduce(
        _add_to_accumulator,
        stations,
        has_vehicles
    )
    has_everything = ft.reduce(
        _add_to_accumulator,
        bases,
        has_vehicles_and_stations
    )

    return has_everything


def _add_to_accumulator(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
                        x: Union[Vehicle, Station, Base]) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
    """
    adds a single Vehicle, Station, or Base to the simulator, unless it is invalid
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

    # x is not a Vehicle, Station, or Request; do not modify simulation
    else:
        failure = SimulationStateError(f"not a Vehicle, Station, or Base: {x}")
        return this_simulation_state, (failure,) + this_failures
