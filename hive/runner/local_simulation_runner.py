from __future__ import annotations

import functools as ft
from typing import NamedTuple, Tuple, Callable, Any, Type

from hive.dispatcher import Dispatcher
from hive.runner import simulation_runner_ops
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.reporting.reporter import Reporter
from hive.state.update import SimulationUpdate


class RunnerPayload(NamedTuple):
    s: SimulationState
    d: Dispatcher


class LocalSimulationRunner(NamedTuple):
    env: Environment

    def run(self,
            initial_simulation_state: SimulationState,
            initial_dispatcher: Dispatcher,
            update_functions: Tuple[SimulationUpdate, ...],
            reporter: Reporter,
            ) -> Tuple[SimulationState, Dispatcher]:
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
            sim_after_updates = ft.reduce(
                lambda s, fn: fn.update(s).simulation_state,
                update_functions,
                payload.s
            )
            updated_sim, updated_dispatcher, instructions = simulation_runner_ops.step(sim_after_updates, payload.d)
            reporter.report(updated_sim, instructions)
            return RunnerPayload(updated_sim, updated_dispatcher)

        final_payload = ft.reduce(
            _run_step,
            time_steps,
            RunnerPayload(initial_simulation_state, initial_dispatcher)
        )

        return final_payload.s, final_payload.d

