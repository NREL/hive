from __future__ import annotations

import functools as ft
import random
from typing import Tuple

import immutables
from h3 import h3

from hive.dispatcher.instruction.instructions import *
from hive.util import Kilometers
from hive.util.helpers import DictOps
from hive.util.helpers import H3Ops

random.seed(123)

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
    from hive.util.typealiases import Report


class InstuctionGenerationResult(NamedTuple):
    instruction_map: immutables.Map = immutables.Map()
    reports: Tuple[Report, ...] = ()
    updated_instruction_generators: Tuple[InstructionGenerator, ...] = ()

    def apply_instruction_generator(self,
                                    instruction_generator: InstructionGenerator,
                                    simulation_state: 'SimulationState') -> InstuctionGenerationResult:
        """
        generates instructions from one InstructionGenerator and updates the result accumulator
        :param instruction_generator: an InstructionGenerator to apply to the SimulationState
        :param simulation_state: the current simulation state
        :return: the updated accumulator
        """
        updated_gen, new_instructions, new_reports = instruction_generator.generate_instructions(simulation_state)

        updated_instruction_map = ft.reduce(
            lambda acc, i: DictOps.add_to_dict(acc, i.vehicle_id, i),
            new_instructions,
            self.instruction_map
        )

        return self._replace(
            instruction_map=updated_instruction_map,
            reports=self.reports + new_reports,
            updated_instruction_generators=self.updated_instruction_generators + (updated_gen,)
        )


def generate_instructions(instruction_generators: Tuple[InstructionGenerator, ...],
                          simulation_state: 'SimulationState',
                          ) -> InstuctionGenerationResult:
    """
    applies a set of InstructionGenerators to the SimulationState. order of generators is preserved
    and has an overwrite behavior with respect to generated Instructions in the instruction_map

    :param instruction_generators:
    :param simulation_state:
    :return: the instructions generated for this time step, which has 0 or 1 instruction per vehicle
    """

    result = ft.reduce(
        lambda acc, gen: acc.apply_instruction_generator(gen, simulation_state),
        instruction_generators,
        InstuctionGenerationResult()
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

    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break

        nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                            entities=simulation_state.bases,
                                            entity_search=simulation_state.b_search,
                                            sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                            max_distance_km=max_search_radius_km)
        if nearest_base:
            instruction = DispatchBaseInstruction(
                vehicle_id=veh.id,
                base_id=nearest_base.id,
            )

            instructions = instructions + (instruction,)
        else:
            # no base found or user set the max search radius too low
            continue

    return instructions


def set_to_reserve(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
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


def charge_at_base(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
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
                charger=Charger.LEVEL_2,
            )

            instructions = instructions + (instruction,)

    return instructions


def instruct_vehicles_dispatch_to_station(n: int,
                                          max_search_radius_km: float,
                                          vehicles: Tuple[Vehicle],
                                          simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to charge at a station

    :param n: how many vehicles to charge at the base
    :param max_search_radius_km: the max kilometers to search for a station
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    instructions = ()

    for veh in vehicles:
        if len(instructions) >= n:
            break

        nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                               entities=simulation_state.stations,
                                               entity_search=simulation_state.s_search,
                                               sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                               max_distance_km=max_search_radius_km,
                                               is_valid=lambda s: s.has_available_charger(Charger.DCFC))
        if nearest_station:
            instruction = DispatchStationInstruction(
                vehicle_id=veh.id,
                station_id=nearest_station.id,
                charger=Charger.DCFC,
            )

            instructions = instructions + (instruction,)

    return instructions


def sit_idle(n: int, vehicles: Tuple[Vehicle]) -> Tuple[Instruction]:
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


def send_vehicle_to_field(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
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
