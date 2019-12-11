from __future__ import annotations

from typing import NamedTuple, Callable

from hive.dispatcher import Dispatcher
from hive.runner import simulation_runner_ops
from hive.runner.run_config import RunConfig
from hive.state.simulation_state import SimulationState

from hive.state import simulation_state_ops
from hive.util.typealiases import Time


class LocalSimulationRunner(NamedTuple):
    dispatcher: Dispatcher
    run_config: RunConfig

    def run(self, initial_simulation_state: SimulationState) -> SimulationState:
        t = self.run_config.sim.start_time_seconds
        sim = initial_simulation_state
        while t < self.run_config.sim.end_time_seconds:

            sim = simulation_runner_ops.step(sim, self.dispatcher)
            t = sim.sim_time

        return sim

