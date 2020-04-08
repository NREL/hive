from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta


class InstructionGenerator(metaclass=ABCNamedTupleMeta):
    """
    A module that produces a set of vehicle instructions based on the state of the simulation
    """

    @abstractmethod
    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        generates vehicle instructions which can perform vehicle state transitions
        based on some objective

        :param simulation_state: The current simulation state

        :return: the updated InstructionGenerator along with generated instructions and any reports
        """
        pass
