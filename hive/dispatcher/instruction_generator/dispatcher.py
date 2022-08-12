from __future__ import annotations
from dataclasses import dataclass

import functools as ft
from typing import Tuple, TYPE_CHECKING, Optional

from hive.dispatcher.instruction_generator import assignment_ops
from hive.state.vehicle_state.charging_base import ChargingBase
from hive.util.typealiases import MembershipId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.model.vehicle.vehicle import Vehicle
    from hive.model.request.request import Request
    from hive.config.dispatcher_config import DispatcherConfig

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction.instructions import DispatchTripInstruction


@dataclass(frozen=True)
class Dispatcher(InstructionGenerator):
    """
    A managers algorithm that assigns vehicles greedily to most expensive request.
    """
    config: DispatcherConfig

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param environment:
        :param simulation_state: The current simulation state
        :return: the updated Dispatcher along with instructions
        """
        base_charging_range_km_threshold = environment.config.dispatcher.base_charging_range_km_threshold

        def _solve_assignment(
                inst_acc: Tuple[DispatchTripInstruction, ...],
                membership_id: Optional[MembershipId],
        ) -> Tuple[DispatchTripInstruction, ...]:
            def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
                vehicle_state_str = vehicle.vehicle_state.__class__.__name__.lower()
                if vehicle_state_str not in environment.config.dispatcher.valid_dispatch_states:
                    return False
                elif not vehicle.driver_state.available:
                    return False
                elif membership_id is not None and not vehicle.membership.grant_access_to_membership_id(membership_id):
                    return False

                mechatronics = environment.mechatronics.get(vehicle.mechatronics_id)
                range_remaining_km = mechatronics.range_remaining_km(vehicle)

                # if we are at a base, do we have enough remaining range to leave the base?
                if isinstance(vehicle.vehicle_state,
                              ChargingBase) and range_remaining_km < base_charging_range_km_threshold:
                    return False
                # do we have enough remaining range to allow us to match?
                return bool(range_remaining_km > environment.config.dispatcher.matching_range_km_threshold)

            def _valid_request(r: Request) -> bool:
                not_already_dispatched = not r.dispatched_vehicle
                valid_access = r.membership.grant_access_to_membership_id(membership_id)
                return not_already_dispatched and valid_access

            # collect the vehicles and requests for the assignment algorithm
            available_vehicles = simulation_state.get_vehicles(
                filter_function=_is_valid_for_dispatch,
            )

            unassigned_requests = simulation_state.get_requests(
                sort=True,
                sort_key=lambda r: r.value,
                sort_reversed=True,
                filter_function=_valid_request,
            )

            # select assignment of vehicles to requests
            solution = assignment_ops.find_assignment(available_vehicles, unassigned_requests,
                                                      assignment_ops.h3_distance_cost)
            instructions = ft.reduce(
                lambda acc, pair: (*acc, DispatchTripInstruction(pair[0], pair[1])),
                solution.solution,
                inst_acc,
            )

            return instructions

        if len(environment.fleet_ids) > 0:
            fleet_ids = environment.fleet_ids
        else:
            fleet_ids = frozenset([None])

        all_instructions = ft.reduce(
            _solve_assignment,
            fleet_ids,
            (),
        )

        return self, all_instructions
