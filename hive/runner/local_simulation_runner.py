from __future__ import annotations

import functools as ft
from typing import NamedTuple, Tuple, Callable, Any, Type

from hive.dispatcher import Dispatcher
from hive.runner import simulation_runner_ops
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.reporting.reporter import Reporter


class RunnerPayload(NamedTuple):
    s: SimulationState
    d: Dispatcher


class LocalSimulationRunner(NamedTuple):
    env: Environment

    def run(self,
            initial_simulation_state: SimulationState,
            initial_dispatcher: Dispatcher,
            reporter: Reporter,
            ) -> Tuple[SimulationState, Dispatcher]:
        """
        steps through time,
        :param initial_simulation_state:
        :param initial_dispatcher:
        :param reporter:
        :return:
        """

        time_steps = range(
            self.env.config.sim.start_time_seconds,
            self.env.config.sim.end_time_seconds,
            self.env.config.sim.timestep_duration_seconds
        )

        def _run_step(payload: RunnerPayload, t: int) -> RunnerPayload:
            """
            inner loop of a LocalSimulationRunner
            :param payload: the sim state and dispatcher state
            :param t: the (expected) time
            :return: the resulting sim state
            """
            updated_sim, updated_dispatcher, instructions = simulation_runner_ops.step(payload.s, payload.d)
            reporter.report(updated_sim, instructions)
            return RunnerPayload(updated_sim, updated_dispatcher)

        final_payload = ft.reduce(
            _run_step,
            time_steps,
            RunnerPayload(initial_simulation_state, initial_dispatcher)
        )

        return final_payload.s, final_payload.d

