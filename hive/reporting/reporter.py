from __future__ import annotations

from abc import ABC, abstractmethod


class Reporter(ABC):
    """
    A class that generates reports for the simulation.
    """

    @abstractmethod
    def log_sim_state(self,
                      sim_state: 'SimulationState',
                      ):
        """
        Takes in a simulation state and generates reports

        :param sim_state: The simulation state.
        :return: Does not return a value.
        """
