from __future__ import annotations

from typing import List

import functools as ft
import random

import h3
import immutables

from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator import assignment_ops
from hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from hive.model.station import Station
from hive.util import Ratio, TupleOps, DictOps
from hive.util.h3_ops import H3Ops

log = logging.getLogger(__name__)

random.seed(123)

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
    from hive.util.typealiases import MembershipId

i_map: immutables.Map[VehicleId, List[Instruction]] = immutables.Map()


class InstructionGenerationResult(NamedTuple):
    instruction_stack: immutables.Map[VehicleId, Tuple[Instruction]] = immutables.Map()
    updated_instruction_generators: Tuple[InstructionGenerator, ...] = ()

    def apply_instruction_generator(self,
                                    instruction_generator: InstructionGenerator,
                                    simulation_state: 'SimulationState',
                                    environment: Environment,
                                    ) -> InstructionGenerationResult:
        """
        generates instructions from one of the InstructionGenerators;
        each of these instructions are added to the stack for the appropriate vehicle id;


        :param instruction_generator: an InstructionGenerator to apply to the SimulationState
        :param simulation_state: the current simulation state
        :param environment: the simulation environment
        :return: the updated accumulator
        """
        updated_gen, new_instructions = instruction_generator.generate_instructions(simulation_state, environment)

        updated_instruction_stack = ft.reduce(
            lambda acc, i: DictOps.add_to_stack_dict(acc, i.vehicle_id, i),
            new_instructions,
            self.instruction_stack
        )

        return self._replace(
            instruction_stack=updated_instruction_stack,
            updated_instruction_generators=self.updated_instruction_generators + (updated_gen,)
        )

    def add_driver_instructions(self, simulation_state, environment):
        """
        drivers are given a chance to optionally generate instructions;
        each of these instructions are added to the stack for the appropriate vehicle id;


        :param simulation_state: the current simulation state
        :param environment: the simulation environment
        :return:
        """
        new_instructions = ft.reduce(
            lambda acc, v: (v.driver_state.generate_instruction(
                simulation_state,
                environment,
                self.instruction_stack.get(v.id),
            ),) + acc,
            simulation_state.get_vehicles(),
            ())

        updated_instruction_stack = ft.reduce(
            lambda acc, i: DictOps.add_to_stack_dict(acc, i.vehicle_id, i) if i else acc,
            new_instructions,
            self.instruction_stack
        )

        return self._replace(
            instruction_stack=updated_instruction_stack,
        )


def generate_instructions(instruction_generators: Tuple[InstructionGenerator, ...],
                          simulation_state: 'SimulationState',
                          environment: Environment,
                          ) -> InstructionGenerationResult:
    """
    applies a set of InstructionGenerators to the SimulationState;
    each time an instruction is generated it gets added to a stack (per vehicle id);
    the last instruction to be added gets popped and executed;
    thus, the order of instruction generation matters as the last instruction generated (per vehicle) gets executed;


    :param instruction_generators: a tuple of instruction generators
    :param simulation_state: the simulation state
    :param environment: the simulation environment
    :return: the instructions generated for this time step (0 to many instructions per vehicle)
    """

    result = ft.reduce(
        lambda acc, gen: acc.apply_instruction_generator(gen, simulation_state, environment),
        instruction_generators,
        InstructionGenerationResult()
    )

    # give drivers a chance to add instructions
    driver_result = result.add_driver_instructions(simulation_state, environment)

    return driver_result


def instruct_vehicles_return_to_base(
        vehicles: Tuple[Vehicle],
        simulation_state: SimulationState,
) -> Tuple[DispatchBaseInstruction, ...]:
    """
    a helper function to send vehicles back to the base

    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    def _base_assignment(
            inst_acc: Tuple[DispatchBaseInstruction, ...],
            membership_id: MembershipId,
    ) -> Tuple[DispatchBaseInstruction, ...]:
        bases = simulation_state.get_bases(membership_id=membership_id)
        member_vehicles = tuple(filter(lambda v: v.membership.is_member(membership_id), vehicles))
        solution = assignment_ops.find_assignment(member_vehicles, bases, assignment_ops.h3_distance_cost)

        instructions = ft.reduce(
            lambda acc, pair: (*acc, DispatchBaseInstruction(pair[0], pair[1])),
            solution.solution,
            inst_acc)

        return instructions

    memberships = set(TupleOps.flatten(tuple(v.membership.as_tuple() for v in vehicles)))

    all_instructions = ft.reduce(
        _base_assignment,
        memberships,
        ()
    )

    return all_instructions


def instruct_vehicles_at_base_to_reserve(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[
    Instruction]:
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


def instruct_vehicles_at_base_to_charge(
        vehicles: Tuple[Vehicle],
        simulation_state: SimulationState,
        environment: Environment,
) -> Tuple[ChargeBaseInstruction]:
    """
    a helper function to set n vehicles to charge at the base

    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :param environment: the environment
    :return:
    """

    def _inner(acc: Tuple[Instruction, ...], veh: Vehicle) -> Tuple[ChargeBaseInstruction, ...]:
        if not isinstance(veh.vehicle_state, ReserveBase):
            return acc
        else:
            base = simulation_state.bases[veh.vehicle_state.base_id]
            if not base.station_id:
                return acc
            else:
                station = simulation_state.stations[base.station_id]
                mechatronics = environment.mechatronics.get(veh.mechatronics_id)

                def _filter_function(cid: ChargerId) -> bool:
                    station_has_charger = bool(station.available_chargers.get(cid))
                    vehicle_can_use_charger = mechatronics.valid_charger(environment.chargers[cid])
                    return station_has_charger and vehicle_can_use_charger

                top_chargers = sorted(filter(
                    _filter_function,
                    environment.chargers.keys()),
                    key=lambda charger_id: -environment.chargers[charger_id].rate)

                if not top_chargers:
                    return acc
                else:
                    top_charger_id = top_chargers[0]

                instruction = ChargeBaseInstruction(
                    vehicle_id=veh.id,
                    base_id=base.id,
                    charger_id=top_charger_id,
                )
                result = acc + (instruction,)
                return result

    instructions = ft.reduce(_inner, vehicles, ())

    return instructions


def instruct_vehicles_to_dispatch_to_station(n: int,
                                             max_search_radius_km: float,
                                             vehicles: Tuple[Vehicle],
                                             simulation_state: SimulationState,
                                             environment: Environment,
                                             target_soc: Ratio,
                                             charging_search_type: ChargingSearchType) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to charge at a station

    :param n: how many vehicles to charge at the base
    :param max_search_radius_km: the max kilometers to search for a station
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :param environment: the simulation environment
    :param target_soc: when ranking alternatives, use this target SoC value
    :param charging_search_type: the type of search to conduct
    :return: instructions for vehicles to charge at stations
    """

    instructions = ()

    for veh in vehicles:
        stations_at_play = TupleOps.flatten(
            tuple(simulation_state.get_stations(membership_id=m) for m in veh.membership.memberships)
        )
        mechatronics = environment.mechatronics.get(veh.mechatronics_id)

        def is_valid_fn(s: Station):
            """
            predicate that tests if a station + vehicle have a matching fleet id, and if so,
            that the station provides chargers which match the vehicle's mechatronics
            :param s: the station to test
            :return: true if the station is valid for this vehicle
            """
            station_matches_fleet_id = s.membership.valid_membership(veh.membership)
            if not station_matches_fleet_id:
                return False
            else:
                station_has_valid_charger = any([
                    mechatronics.valid_charger(environment.chargers.get(cid)) for cid in s.total_chargers.keys()
                ])
                return station_has_valid_charger

        if len(instructions) >= n:
            break

        if charging_search_type == ChargingSearchType.NEAREST_SHORTEST_QUEUE:
            # use the simple weighted euclidean distance ranking

            top_chargers = sorted(filter(
                lambda cid: mechatronics.valid_charger(environment.chargers[cid]),
                environment.chargers.keys()),
                key=lambda charger_id: -environment.chargers[charger_id].rate)

            if not top_chargers:
                # no valid chargers exist for this vehicle
                break
            else:
                top_charger_id = top_chargers[0]

            cache = ft.reduce(
                lambda acc, station_id: acc.update({station_id: top_charger_id}),
                [station.id for station in stations_at_play],
                immutables.Map()
            )

            distance_fn = assignment_ops.nearest_shortest_queue_ranking(veh, top_charger_id)

        else:  # charging_search_type == ChargingSearchType.SHORTEST_TIME_TO_CHARGE:
            # use the search-based metric which considers travel, queueing, and charging time

            def v_fn(s: Station):
                station_has_valid_charger = any([
                    mechatronics.valid_charger(environment.chargers.get(cid)) for cid in s.total_chargers.keys()
                ])
                return station_has_valid_charger

            distance_fn, cache = assignment_ops.shortest_time_to_charge_ranking(
                vehicle=veh, sim=simulation_state, env=environment, target_soc=target_soc
            )

        nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                               entities=stations_at_play,
                                               entity_search=simulation_state.s_search,
                                               sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                               max_search_distance_km=max_search_radius_km,
                                               is_valid=is_valid_fn,
                                               distance_function=distance_fn)
        if nearest_station:
            best_charger_id = cache.get(nearest_station.id)

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


def instruct_vehicles_to_reposition(n: int, vehicles: Tuple[Vehicle], simulation_state: SimulationState) -> Tuple[
    Instruction]:
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
