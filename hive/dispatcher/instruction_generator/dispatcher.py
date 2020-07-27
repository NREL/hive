from __future__ import annotations

from typing import Tuple, NamedTuple, TYPE_CHECKING
import functools as ft
import h3

from hive.dispatcher.instruction_generator import assignment_ops
from hive.model.request import Request
from hive.state.vehicle_state.charging_base import ChargingBase

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.model.vehicle.vehicle import Vehicle
    from hive.config.dispatcher_config import DispatcherConfig

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction.instructions import DispatchTripInstruction
from hive.util.helpers import H3Ops


class Dispatcher(NamedTuple, InstructionGenerator):
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

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            vehicle_state_str = vehicle.vehicle_state.__class__.__name__.lower()
            if vehicle_state_str not in environment.config.dispatcher.valid_dispatch_states:
                return False

            mechatronics = environment.mechatronics.get(vehicle.mechatronics_id)
            range_remaining_km = mechatronics.range_remaining_km(vehicle)

            # if we are at a base, do we have enough remaining range to leave the base?
            if isinstance(vehicle.vehicle_state, ChargingBase) and range_remaining_km < base_charging_range_km_threshold:
                return False
            # do we have enough remaining range to allow us to match?
            return bool(range_remaining_km > environment.config.dispatcher.matching_range_km_threshold)

        # collect the vehicles and requests for the assignment algorithm
        available_vehicles = simulation_state.get_vehicles(filter_function=_is_valid_for_dispatch)
        unassigned_requests = simulation_state.get_requests(
            sort=True,
            sort_key=lambda r: r.value,
            sort_reversed=True,
            filter_function=lambda r: not r.dispatched_vehicle
        )

        # select assignment of vehicles to requests
        solution = assignment_ops.find_assignment(available_vehicles, unassigned_requests, assignment_ops.h3_distance_cost)
        instructions = ft.reduce(lambda acc, pair: (*acc, DispatchTripInstruction(pair[0], pair[1])), solution.solution, ())

        return self, instructions
