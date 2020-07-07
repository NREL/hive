from __future__ import annotations

import random
from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_return_to_base,
)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.model.vehicle.vehicle import Vehicle
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.config.dispatcher_config import DispatcherConfig

random.seed(123)


class IdleTimeOut(NamedTuple, InstructionGenerator):
    """
    A class that sends vehicles to reserve.
    """
    config: DispatcherConfig

    # 15 minutes
    max_idle_seconds = 900

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param environment:
        :param simulation_state: The current simulation state

        :return: the updated PositionFleetManger along with instructions
        """

        def idle_time_out(v: Vehicle) -> bool:
            name = v.vehicle_state.__class__.__name__.lower()
            if name == "idle":
                return v.vehicle_state.idle_duration > self.max_idle_seconds
            else:
                return False

        time_out_vehicles = simulation_state.get_vehicles(
            filter_function=idle_time_out,
        )

        instructions = instruct_vehicles_return_to_base(
            len(time_out_vehicles),
            self.config.max_search_radius_km,
            time_out_vehicles,
            simulation_state
        )

        return self, instructions
