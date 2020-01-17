from __future__ import annotations

import functools as ft
from typing import Type, Union, Tuple, cast

from hive.dispatcher.instruction import Instruction
from hive.model.base import Base
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.energy.powercurve.powercurve import Powercurve
from hive.state.simulation_state import SimulationState
from hive.util.exception import *
from hive.util.typealiases import SimTime
from hive.util.units import seconds


def apply_instructions(simulation_state: SimulationState, instructions: Tuple[Instruction, ...]) -> SimulationState:
    """
    applies all the instructions to the simulation state, ignoring the ones that fail

    :param simulation_state: the sim state
    :param instructions: dispatcher instructions
    :return: the sim state with vehicle intentions updated
    """
    return ft.reduce(
        _add_instruction,
        instructions,
        simulation_state
    )


def _add_instruction(simulation_state: SimulationState, instruction: Instruction) -> SimulationState:
    """
    inner loop for apply_instructions method

    :param simulation_state: the intermediate sim state
    :param instruction: the ith instruction
    :return: sim state with the ith instruction added, unless it's bogus
    """
    updated_sim = simulation_state.apply_instruction(instruction)
    if updated_sim is None:
        return simulation_state
    else:
        return updated_sim


def initial_simulation_state(
        road_network: RoadNetwork,
        vehicles: Tuple[Vehicle, ...] = (),
        stations: Tuple[Station, ...] = (),
        bases: Tuple[Base, ...] = (),
        powertrains: Tuple[Powertrain, ...] = (),
        powercurves: Tuple[Powercurve, ...] = (),
        start_time: SimTime = 0,
        sim_timestep_duration_seconds: seconds = 1,
        sim_h3_location_resolution: int = 15,
        sim_h3_search_resolution: int = 7,
) -> Tuple[SimulationState, Tuple[SimulationStateError, ...]]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network

    :param powercurves: 
    :param powertrains: 
    :param road_network: the (initial) road network
    :param vehicles: the vehicles available in this simulation
    :param stations: the stations available in this simulation
    :param bases: the bases available in this simulation
    :param start_time: the start time for this simulation (by default, time step 0)
    :param sim_timestep_duration_seconds: the size of a time step in seconds
    :param sim_h3_location_resolution: the h3 resolution for internal positioning (comparison ops can override)
    :param sim_h3_search_resolution: the h3 upper-resolution for the bi-level location search
    :return: a SimulationState, or a SimulationStateError
    """

    # copy in fields which do not require additional work
    simulation_state_builder = SimulationState(
        road_network=road_network,
        initial_sim_time=start_time,
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_location_resolution=sim_h3_location_resolution,
        sim_h3_search_resolution=sim_h3_search_resolution
    )
    failures: Tuple[SimulationStateError, ...] = tuple()

    # add vehicles, stations, bases, powertrains, and powercurves
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
    has_powertrains = ft.reduce(
        _add_to_builder,
        powertrains,
        has_bases
    )
    has_everything = ft.reduce(
        _add_to_builder,
        powercurves,
        has_powertrains
    )

    return has_everything


def _add_to_builder(acc: Tuple[SimulationState, Tuple[SimulationStateError, ...]],
                    x: Union[Vehicle, Station, Base, Type[Powertrain], Type[Powercurve]]) \
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

    # add a Powertrain
    elif issubclass(type(x), Powertrain):
        powertrain = cast(Powertrain, x)
        result = this_simulation_state.add_powertrain(powertrain)
        if isinstance(result, SimulationStateError):
            return this_simulation_state, (result,) + this_failures
        else:
            return result, this_failures

    # add a Powercurve
    elif issubclass(type(x), Powercurve):
        powercurve = cast(Powercurve, x)
        result = this_simulation_state.add_powercurve(powercurve)
        if isinstance(result, SimulationStateError):
            return this_simulation_state, (result,) + this_failures
        else:
            return result, this_failures

    # x is something else; do not modify simulation
    else:
        failure = SimulationStateError(f"not a Vehicle, Station, Base, Powertrain, or Powercurve: {x}")
        return this_simulation_state, (failure,) + this_failures
