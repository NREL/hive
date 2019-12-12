from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.util.typealiases import RequestId
# from hive.simulationstate.simulation_state import SimulationState


class Dispatcher(ABC):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    @abstractmethod
    def generate_instructions(self, simulation_state: 'SimulationState') -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        """
        Generates instructions for a given simulation state.
        :param simulation_state:
        :return: the updated Dispatcher along with all instructions for this time step
        """
        pass
