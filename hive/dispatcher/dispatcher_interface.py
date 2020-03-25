from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.instruction import Instruction


class DispatcherInterface(metaclass=ABCNamedTupleMeta):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    @abstractmethod
    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[DispatcherInterface, Tuple[Instruction, ...], Tuple[dict, ...]]:
        """
        Generates instructions for a given simulation state.

        :param simulation_state:
        :param env:
        :return: the updated Dispatcher along with all instructions for this time step and reports
        """
