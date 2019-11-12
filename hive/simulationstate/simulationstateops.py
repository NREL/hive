from __future__ import annotations
from copy import copy
from typing import NamedTuple, Dict, Optional, Union, Tuple, List, cast
import functools as ft

from hive.model.base import Base
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.simulationstate.simulationstate import SimulationState
from hive.util.typealiases import *
from hive.util.exception import *
from h3 import h3


def initial_simulation_state(
        vehicles: Tuple[Vehicle, ...],
        stations: Tuple[Station, ...],
        bases: Tuple[Base, ...],
        road_network: RoadNetwork,
        start_time: int = 0,
        sim_h3_resolution: Optional[int] = 11
) -> Tuple[SimulationState, Tuple[SimulationStateError]]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network
    :param vehicles: the vehicles available in this simulation
    :param stations:
    :param bases:
    :param road_network: the (initial) road network
    :param start_time: the start time for this simulation (by default, time step 0)
    :param sim_h3_resolution: the h3 resolution for internal positioning (comparison ops can override)
    :return: a SimulationState, or a SimulationStateError
    """

    # copy in fields which do not require additional work
    simulation_state_builder = SimulationState(
        road_network=road_network,
        sim_time=start_time,
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

    # unpack accumulator
    this_simulation_state: SimulationState = acc[0]
    this_failures: Tuple[SimulationStateError, ...] = acc[1]

    # side effect, since i can't directly evaluate from an if/elif/else
    result = None
    if isinstance(x, Vehicle):
        vehicle = cast(Vehicle, x)
        result = this_simulation_state.add_vehicle(vehicle)
    elif isinstance(x, Station):
        station = cast(Station, x)
        result = this_simulation_state.add_station(station)
    elif isinstance(x, Base):
        base = cast(Base, x)
        result = this_simulation_state.add_base(base)
    else:
        result

    if isinstance(result, SimulationStateError):
        # pass along failure
        return this_simulation_state, result + this_failures
    else:
        return result, this_failures

#
# def _add_veh_to_accumulator(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
#                             veh: Vehicle) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
#     this_simulation_state: SimulationState = acc[0]
#     this_failures: Tuple[SimulationStateError, ...] = acc[1]
#
#     add_veh_result = this_simulation_state.add_vehicle(veh)
#     if type(add_veh_result) == type(Exception):
#         updated_failures = add_veh_result + this_failures
#         return this_simulation_state, updated_failures
#     else:
#         return add_veh_result, this_failures
#
#
# def _add_station_to_accumulator(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
#                             s: Station) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
#     this_simulation_state: SimulationState = acc[0]
#     this_failures: Tuple[SimulationStateError, ...] = acc[1]
#
#     add_station_result = this_simulation_state.add_station(s)
#     if type(add_station_result) == type(Exception):
#         updated_failures = add_station_result + this_failures
#         return this_simulation_state, updated_failures
#     else:
#         return add_station_result, this_failures
#
# def _add_base_to_accumulator(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
#                             s: Station) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
#     this_simulation_state: SimulationState = acc[0]
#     this_failures: Tuple[SimulationStateError, ...] = acc[1]
#
#     add_station_result = this_simulation_state.add_station(s)
#     if type(add_station_result) == type(Exception):
#         updated_failures = add_station_result + this_failures
#         return this_simulation_state, updated_failures
#     else:
#         return add_station_result, this_failures
