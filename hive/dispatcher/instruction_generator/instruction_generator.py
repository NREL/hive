from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

InstructionGeneratorId = str

class InstructionGenerator(metaclass=ABCNamedTupleMeta):
    """
    A module that produces a set of vehicle instructions based on the state of the simulation
    """

    @abstractmethod
    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...]]:
        """
        generates vehicle instructions which can perform vehicle state transitions
        based on some objective

        :param simulation_state: the current simulation state
        :param environment: the simulation environment

        :return: the updated InstructionGenerator along with generated instructions
        """
        pass
