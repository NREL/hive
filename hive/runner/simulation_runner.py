from __future__ import annotations

from typing import NamedTuple, Callable

from hive.dispatcher import Dispatcher
from hive.simulationstate.simulationstate import SimulationState
from hive.util.typealiases import Time


class LocalSimulationRunner(NamedTuple):
    simulation_state: SimulationState
    dispatcher: Dispatcher

    def run(self, end_time: Time) -> LocalSimulationRunner:
        pass

    def step(self) -> LocalSimulationRunner:
        """
        take one step in the simulation
        :return:
        """
        instructions = self.dispatcher.generate_instructions(self.simulation_state)
