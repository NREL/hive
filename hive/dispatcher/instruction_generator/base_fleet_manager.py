from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import instruct_vehicles_at_base_to_charge
from hive.model.energy.energytype import EnergyType
from hive.state.vehicle_state.reserve_base import ReserveBase

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.config.dispatcher_config import DispatcherConfig

log = logging.getLogger(__name__)


class BaseFleetManager(NamedTuple, InstructionGenerator):
    """
    A manager that instructs vehicles on how to behave at the base
    """
    config: DispatcherConfig

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[BaseFleetManager, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param environment:
        :param simulation_state: The current simulation state

        :return: the updated BaseFleetManager along with instructions
        """

        reserve_vehicles = simulation_state.get_vehicles(
            sort=True,
            sort_key=lambda v: v.energy.get(EnergyType.ELECTRIC) if v.energy.get(EnergyType.ELECTRIC) else 0,
            filter_function=lambda v: isinstance(v.vehicle_state, ReserveBase),
        )

        target = len(reserve_vehicles)

        charge_instructions = instruct_vehicles_at_base_to_charge(target, reserve_vehicles, simulation_state)

        return self, charge_instructions
