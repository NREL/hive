from __future__ import annotations

import functools as ft
from typing import NamedTuple, TYPE_CHECKING, Callable, Optional
import logging

from hive.runner.runner_payload import RunnerPayload

if TYPE_CHECKING:
    from hive.runner.environment import Environment
    from hive.reporting.reporter import Reporter

log = logging.getLogger(__name__)


class LocalSimulationRunner(NamedTuple):
    """
    The local simulation runner.

    :param env: The environment variables.
    :type env: :py:obj:`Environment`
    """
    env: Environment

    def run(self,
            runner_payload: RunnerPayload,
            reporter: Reporter,
            ) -> RunnerPayload:
        """
        steps through time, running a simulation, and producing a simulation result

        :param runner_payload: the initial state of the simulation
        :param reporter: a class to report messages from the simulation
        :return: the final simulation state and dispatcher state
        """

        time_steps = range(
            self.env.config.sim.start_time,
            self.env.config.sim.end_time,
            self.env.config.sim.timestep_duration_seconds,
        )

        final_payload = ft.reduce(
            _run_step_in_context(self.env, reporter),
            time_steps,
            runner_payload
        )

        return final_payload

    def step(self,
             runner_payload: RunnerPayload,
             reporter: Reporter
             ) -> Optional[RunnerPayload]:
        """
        takes exactly one step forward, or, if the simulation has reached the end time, does nothing

        :param runner_payload: the current state of the simulation
        :param reporter: a class to report messages from the simulation
        :return: the next simulation state after one simtime step, or, None if we have reached the end_time
        """
        if runner_payload.s.sim_time == self.env.config.sim.end_time:
            return None
        else:
            return _run_step_in_context(self.env, reporter)(runner_payload)


def _run_step_in_context(env: Environment, reporter: Reporter) -> Callable:
    def _run_step(payload: RunnerPayload, t: int) -> RunnerPayload:

        # applies the most recent version of each update function
        updated_payload = payload.u.apply_update(payload)
        updated_sim = updated_payload.s

        reporter.report(updated_sim, updated_payload.r)
        if updated_sim.sim_time % 3600 == 0:
            log.info(f"simulating {updated_sim.sim_time} of {env.config.sim.end_time} seconds")
        return updated_payload.clear_reports()

    return _run_step
