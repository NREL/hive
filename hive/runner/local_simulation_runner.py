from __future__ import annotations

import functools as ft
from typing import NamedTuple, Tuple, Callable, Any, Type

from hive.dispatcher import DispatcherInterface
from hive.runner import simulation_runner_ops
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.reporting.reporter import Reporter
from hive.state.update import SimulationUpdateFunction


class RunnerPayload(NamedTuple):
    """
    Holds the simulation state, dispatcher and reports for the simulation run.

    :param s: the simulation state
    :type s: :py:obj:`SimulationState`
    :param d: the dispatcher
    :type d: :py:obj:`Dispatcher`
    :param r: any reports generated for a timestep
    :type r: :py:obj:`Tuple[str, ...]`
    """
    s: SimulationState
    d: DispatcherInterface
    f: Tuple[SimulationUpdateFunction, ...]
    r: Tuple[str, ...] = ()

    def apply_fn(self, fn: SimulationUpdateFunction) -> RunnerPayload:
        """
        applies an update function to this payload. if the update function
        was also updated, then store the updated version of the update function
        invariant: the update functions (self.f) were emptied before applying these
        (we don't want to duplicate them!)
        :param fn: an update function
        :return: the updated payload, with update function applied to the simulation,
        and the update function possibly updated itself
        """
        result, updated_fn = fn.update(self.s)
        next_update_fns = self.f + (updated_fn, ) if updated_fn else self.f + (fn, )
        updated_payload = self._replace(
            s=result.simulation_state,
            r=self.r + result.reports,
            f=next_update_fns
        )
        return updated_payload

    def apply_update_functions(self) -> RunnerPayload:
        """
        apply one time step of the update functions
        :return: the RunnerPayload with SimulationState and update functions (SimulationUpdateFunction) updated
        """
        return ft.reduce(
            lambda acc, fn: acc.apply_fn(fn),
            self.f,
            self._replace(f=())
        )


class LocalSimulationRunner(NamedTuple):
    """
    The local simulation runner.

    :param env: The environment variables.
    :type env: :py:obj:`Environment`
    """
    env: Environment

    def run(self,
            initial_simulation_state: SimulationState,
            initial_dispatcher: DispatcherInterface,
            update_functions: Tuple[SimulationUpdateFunction, ...],
            reporter: Reporter,
            ) -> RunnerPayload:
        """
        steps through time, running a simulation, and producing a simulation result

        :param initial_simulation_state: the simulation state before the day has begun
        :param initial_dispatcher: the initialized dispatcher
        :param update_functions: applied at the beginning of each time step to modify the sim
        :param reporter: a class to report messages from the simulation
        :return: the final simulation state and dispatcher state
        """

        time_steps = range(
            self.env.config.sim.start_time_seconds,
            self.env.config.sim.end_time_seconds
        )

        def _run_step(payload: RunnerPayload, t: int) -> RunnerPayload:

            updated_payload = payload.apply_update_functions()

            updated_sim, updated_dispatcher, instructions = simulation_runner_ops.step(updated_payload.s,
                                                                                       updated_payload.d)
            reporter.report(updated_sim, instructions, updated_payload.r)
            if updated_sim.sim_step % 100 == 0:
                print(f"running step {updated_sim.sim_step} of {len(time_steps)}")
            return RunnerPayload(s=updated_sim, d=updated_dispatcher, f=updated_payload.f, r=())

        final_payload = ft.reduce(
            _run_step,
            time_steps,
            RunnerPayload(initial_simulation_state, initial_dispatcher, update_functions)
        )

        return final_payload
