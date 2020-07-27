from __future__ import annotations

import functools as ft
import random

import immutables
import h3

from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator import assignment_ops
from hive.model.station import Station
from hive.util import Kilometers, Ratio
from hive.util.helpers import DictOps, H3Ops

random.seed(123)

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator


class InstructionGenerationResult(NamedTuple):
    instruction_map: immutables.Map = immutables.Map()
    updated_instruction_generators: Tuple[InstructionGenerator, ...] = ()

    def apply_instruction_generator(self,
                                    instruction_generator: InstructionGenerator,
                                    simulation_state: 'SimulationState',
                                    environment: Environment,
                                    ) -> InstructionGenerationResult:
        """
        generates instructions from one InstructionGenerator and updates the result accumulator
        :param environment:
        :param instruction_generator: an InstructionGenerator to apply to the SimulationState
        :param simulation_state: the current simulation state
        :return: the updated accumulator
        """
        updated_gen, new_instructions = instruction_generator.generate_instructions(simulation_state, environment)

        updated_instruction_map = ft.reduce(
            lambda acc, i: DictOps.add_to_dict(acc, i.vehicle_id, i),
            new_instructions,
            self.instruction_map
        )

        return self._replace(
            instruction_map=updated_instruction_map,
            updated_instruction_generators=self.updated_instruction_generators + (updated_gen,)
        )


def generate_instructions(instruction_generators: Tuple[InstructionGenerator, ...],
                          simulation_state: 'SimulationState',
                          environment: Environment,
                          ) -> InstructionGenerationResult:
    """
    applies a set of InstructionGenerators to the SimulationState. order of generators is preserved
    and has an overwrite behavior with respect to generated Instructions in the instruction_map

    :param instruction_generators:
    :param simulation_state:
    :param environment:
    :return: the instructions generated for this time step, which has 0 or 1 instruction per vehicle
    """

    result = ft.reduce(
        lambda acc, gen: acc.apply_instruction_generator(gen, simulation_state, environment),
        instruction_generators,
        InstructionGenerationResult()
    )

    return result


def instruct_vehicles_return_to_base(n: int,
                                     max_search_radius_km: Kilometers,
                                     vehicles: Tuple[Vehicle],
                                     simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to send n vehicles back to the base

    :param n: how many vehicles to send back to base
    :param max_search_radius_km: the maximum distance vehicles will search to a base
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    bases = tuple(simulation_state.bases.values())

    solution = assignment_ops.find_assignment(vehicles, bases, assignment_ops.h3_distance_cost)
    instructions = ft.reduce(lambda acc, pair: (*acc, DispatchBaseInstruction(pair[0], pair[1])), solution.solution, ())

    return instructions


def instruct_vehicles_at_base_to_reserve(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to reserve at the base

    :param n: how many vehicles to set to reserve
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """
    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break

        base_id = simulation_state.b_locations[veh.geoid]
        instruction = ReserveBaseInstruction(
            vehicle_id=veh.id,
            base_id=base_id,
        )

        instructions = instructions + (instruction,)

    return instructions


def instruct_vehicles_at_base_to_charge(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to charge at the base

    :param n: how many vehicles to charge at the base
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """
    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break
        base_id = simulation_state.b_locations[veh.geoid]
        base = simulation_state.bases[base_id]
        if base.station_id:
            instruction = ChargeBaseInstruction(
                vehicle_id=veh.id,
                base_id=base.id,
                charger_id="LEVEL_2",
            )

            instructions = instructions + (instruction,)

    return instructions


def instruct_vehicles_to_dispatch_to_station(n: int,
                                             max_search_radius_km: float,
                                             vehicles: Tuple[Vehicle],
                                             simulation_state: SimulationState,
                                             environment: Environment,
                                             target_soc: Ratio) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to charge at a station

    :param n: how many vehicles to charge at the base
    :param max_search_radius_km: the max kilometers to search for a station
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :param environment: the simulation environment
    :param target_soc: when ranking alternatives, use this target SoC value
    :return: instructions for vehicles to charge at stations
    """

    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break

        # construct a distance function rooted on finding the shortest time to
        # recharge for this vehicle
        # use this "cache" to cache the best charger type to pick for use
        # at the chosen station, as a side effect
        distance_fn, cache = assignment_ops.shortest_time_to_charge_ranking(
            vehicle=veh, sim=simulation_state, env=environment, target_soc=target_soc
        )

        nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                               entities=simulation_state.stations,
                                               entity_search=simulation_state.s_search,
                                               sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                               max_search_distance_km=max_search_radius_km,
                                               distance_function=distance_fn)
        if nearest_station:

            best_charger_id = cache.get("best_charger_id")

            instruction = DispatchStationInstruction(
                vehicle_id=veh.id,
                station_id=nearest_station.id,
                charger_id=best_charger_id,
            )

            instructions = instructions + (instruction,)

    return instructions


def instruct_vehicles_to_sit_idle(n: int, vehicles: Tuple[Vehicle]) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to sit idle

    :param n: how many vehicles to change to idle
    :param vehicles: the list of vehicles to consider
    :return:
    """
    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break
        instruction = IdleInstruction(
            vehicle_id=veh.id,
        )

        instructions = instructions + (instruction,)

    return instructions


def instruct_vehicles_to_reposition(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to send n vehicles into the field at a random location

    :param n: how many vehicles to send to the field
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    def _sample_random_location(road_network) -> GeoId:
        random_hex = random.choice(tuple(road_network.geofence.geofence_set))
        children = h3.h3_to_children(random_hex, road_network.sim_h3_resolution)
        choice = random.choice(tuple(children))
        return choice

    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break
        random_location = _sample_random_location(simulation_state.road_network)
        instruction = RepositionInstruction(vehicle_id=veh.id, destination=random_location)
        instructions = instructions + (instruction,)

    return instructions
