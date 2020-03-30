from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.util.typealiases import Report


class DispatcherInterface(metaclass=ABCNamedTupleMeta):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    @abstractmethod
    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[DispatcherInterface, InstructionMap, Tuple[Report, ...]]:
        """
        Generates instructions for a given simulation state.

        :param simulation_state: the state of the simulation

        :return: the updated Dispatcher along with all instructions for this time step and reports
        """
