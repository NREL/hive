from abc import ABC, abstractmethod
from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.util.typealiases import RequestId
from hive.simulationstate.simulationstate import SimulationState


class Dispatcher(ABC):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    @abstractmethod
    def generate_instructions(self, simulation_state: SimulationState) -> Tuple[Instruction, ...]:
        """
        Generates instructions for a given simulation state.
        :param simulation_state:
        :return:
        """
        pass
