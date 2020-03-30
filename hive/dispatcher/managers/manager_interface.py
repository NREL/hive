from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta


class ManagerInterface(metaclass=ABCNamedTupleMeta):
    """
    A class that computes an optimal fleet state.
    """

    @abstractmethod
    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[ManagerInterface, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state
        :param previous_instructions: instructions from previous modules

        :return: the updated Manager along with fleet targets and reports
        """
        pass
