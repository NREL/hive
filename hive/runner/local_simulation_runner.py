from __future__ import annotations

import functools as ft
from typing import NamedTuple, TYPE_CHECKING, Callable, Optional

from hive.runner.runner_payload import RunnerPayload

if TYPE_CHECKING:
    from hive.runner.environment import Environment


class LocalSimulationRunner(NamedTuple):
    """
    The local simulation runner.
    """

    @classmethod
    def run(cls,
            runner_payload: RunnerPayload,
            ) -> RunnerPayload:
        """
        steps through time, running a simulation, and producing a simulation result

        :param runner_payload: the initial state of the simulation
        :return: the final simulation state and dispatcher state
        """

        time_steps = range(
            runner_payload.e.config.sim.start_time,
            runner_payload.e.config.sim.end_time,
            runner_payload.e.config.sim.timestep_duration_seconds,
        )

        final_payload = ft.reduce(
            _run_step_in_context(runner_payload.e),
            time_steps,
            runner_payload
        )

        return final_payload

    @classmethod
    def step(cls, runner_payload: RunnerPayload) -> Optional[RunnerPayload]:
        """
        takes exactly one step forward, or, if the simulation has reached the end time, does nothing

        :param runner_payload: the current state of the simulation
        :return: the next simulation state after one simtime step, or, None if we have reached the end_time
        """
        if runner_payload.s.sim_time >= runner_payload.e.config.sim.end_time:
            return None
        else:
            return _run_step_in_context(runner_payload.e)(runner_payload)


def _run_step_in_context(env: Environment) -> Callable:
    def _run_step(payload: RunnerPayload, t: int = -1) -> RunnerPayload:

        # applies the most recent version of each update function
        updated_payload, reports = payload.u.apply_update(payload)
        updated_sim = updated_payload.s
        if isinstance(updated_sim, Exception):
            raise (updated_sim)

        env.reporter.log_sim_state(updated_sim)
        if updated_sim.sim_time % 3600 == 0:
            # this should use the run logger instead of printing
            print(f"simulating {updated_sim.sim_time} of {env.config.sim.end_time} seconds")
        return updated_payload

    return _run_step
