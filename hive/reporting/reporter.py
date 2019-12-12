from __future__ import annotations

from typing import Tuple
from abc import ABC, abstractmethod

from hive.simulationstate.simulation_state import SimulationState
from hive.dispatcher.instruction import Instruction


class Reporter(ABC):
    """
    A class that generates reports for the simulation.
    """

    @abstractmethod
    def report(self, sim_state: SimulationState, instructions: Tuple[Instruction, ...]):
        """
        Takes in a simulation state and a tuple of instructions and writes the appropriate information.
        :param sim_state:
        :param instructions:
        :return:
        """
        pass
