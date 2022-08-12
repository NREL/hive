from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction


InstructionGeneratorId = str


class InstructionGenerator(ABC):
    """
    A module that produces a set of vehicle instructions based on the state of the simulation
    """

    @property
    def name(self) -> str:
        """
        Defacto ID for any instruction generator is the class name
        """
        return self.__class__.__name__

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
