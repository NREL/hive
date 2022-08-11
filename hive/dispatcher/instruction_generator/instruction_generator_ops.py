from __future__ import annotations

import functools as ft
import random
from typing import List, Callable

import immutables

from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator import assignment_ops
from hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from hive.model.station.station import Station
from hive.util.typealiases import GeoId
from hive.util import Ratio, DictOps
from hive.util.h3_ops import H3Ops
from hive.util.units import Kilometers

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
            simulation_state.vehicles.values(),
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


def valid_station_for_vehicle(vehicle: Vehicle, env: Environment) -> Callable[[Station], bool]:
    """
    only allows vehicles to use stations where the membership is correct
    and the fuel type is correct
    :param vehicle: the vehicle
    :param env: simulation environment
    :return: valid station function
    """
    mechatronics = env.mechatronics.get(vehicle.mechatronics_id)

    def _inner(station: Station):
        vehicle_has_access = station.membership.grant_access_to_membership(vehicle.membership)
        if not vehicle_has_access:
            return False
        else:
            station_has_valid_charger = any([
                mechatronics.valid_charger(env.chargers.get(cid)) for cid in station.state.keys()
            ])
            return station_has_valid_charger
    return _inner


def instruct_vehicles_to_dispatch_to_station(n: int,
                                             max_search_radius_km: float,
                                             vehicles: Tuple[Vehicle, ...],
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

        if len(instructions) >= n:
            break

        if charging_search_type == ChargingSearchType.NEAREST_SHORTEST_QUEUE:
            # use the simple weighted euclidean distance ranking

            distance_fn = assignment_ops.nearest_shortest_queue_distance(veh, environment)

        else:  # charging_search_type == ChargingSearchType.SHORTEST_TIME_TO_CHARGE:
            # use the search-based metric which considers travel, queueing, and charging time

            distance_fn = assignment_ops.shortest_time_to_charge_distance(
                vehicle=veh, sim=simulation_state, env=environment, target_soc=target_soc
            )

        nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                               entities=simulation_state.stations.values(),
                                               entity_search=simulation_state.s_search,
                                               sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                               max_search_distance_km=max_search_radius_km,
                                               is_valid=valid_station_for_vehicle(veh, environment),
                                               distance_function=distance_fn)
        if nearest_station:
            # get the best charger id for this station. re-computes distance ranking one last time
            # this could be removed if our nearest entity search also returned the best charger id
            # these both could return "None" but that shouldn't be possible if we found a nearest station
            if charging_search_type == ChargingSearchType.NEAREST_SHORTEST_QUEUE:
                best_charger_id, best_charger_rank = assignment_ops.nearest_shortest_queue_ranking(veh, nearest_station, environment)
            else:  # charging_search_type == ChargingSearchType.SHORTEST_TIME_TO_CHARGE:
                best_charger_id, best_charger_rank = assignment_ops.shortest_time_to_charge_ranking(
                    vehicle=veh, station=nearest_station, sim=simulation_state, env=environment, target_soc=target_soc
                )

            instruction = DispatchStationInstruction(
                vehicle_id=veh.id,
                station_id=nearest_station.id,
                charger_id=best_charger_id,
            )

            instructions = instructions + (instruction,)

    return instructions


def get_nearest_valid_station_distance(max_search_radius_km: float,
                                       vehicle: Vehicle,
                                       geoid: GeoId,
                                       simulation_state: SimulationState,
                                       environment: Environment,
                                       target_soc: Ratio,
                                       charging_search_type: ChargingSearchType) -> Kilometers:
    """
        a helper function to find the distance between a vehicle and the closest valid station

        :param max_search_radius_km: the max kilometers to search for a station
        :param vehicle: the vehicle to consider
        :param geoid: the geoid of the origin
        :param simulation_state: the simulation state
        :param environment: the simulation environment
        :param target_soc: when ranking alternatives, use this target SoC value
        :param charging_search_type: the type of search to conduct
        :return: the distance in km to the nearest valid station
        """

    if charging_search_type == ChargingSearchType.NEAREST_SHORTEST_QUEUE:
        # use the simple weighted euclidean distance ranking

        distance_fn = assignment_ops.nearest_shortest_queue_distance(vehicle, environment)

    else:  # charging_search_type == ChargingSearchType.SHORTEST_TIME_TO_CHARGE:
        # use the search-based metric which considers travel, queueing, and charging time

        distance_fn, cache = assignment_ops.shortest_time_to_charge_distance(
            vehicle=vehicle, sim=simulation_state, env=environment, target_soc=target_soc
        )

    nearest_station = H3Ops.nearest_entity(geoid=geoid,
                                           entities=simulation_state.stations.values(),
                                           entity_search=simulation_state.s_search,
                                           sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                           max_search_distance_km=max_search_radius_km,
                                           is_valid=valid_station_for_vehicle(vehicle, environment),
                                           distance_function=distance_fn)

    if nearest_station:
        return simulation_state.road_network.distance_by_geoid_km(origin=geoid, destination=nearest_station.geoid)

    return 99999999999999
