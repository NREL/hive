from __future__ import annotations

import functools as ft

from typing import NamedTuple, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.runner.environment import Environment
    from hive.state.simulation_state import SimulationState
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
    f: Tuple[SimulationUpdateFunction, ...]
    r: Tuple[str, ...] = ()

    def apply_fn(self, fn: SimulationUpdateFunction, env: Environment) -> RunnerPayload:
        """
        applies an update function to this payload. if the update function
        was also updated, then store the updated version of the update function
        invariant: the update functions (self.f) were emptied before applying these
        (we don't want to duplicate them!)
        :param fn: an update function
        :param env: the simulation environment
        :return: the updated payload, with update function applied to the simulation,
        and the update function possibly updated itself
        """
        result, updated_fn = fn.update(self.s, env)
        next_update_fns = self.f + (updated_fn,) if updated_fn else self.f + (fn,)
        updated_payload = self._replace(
            s=result.simulation_state,
            r=self.r + result.reports,
            f=next_update_fns
        )
        return updated_payload

    def apply_update_functions(self, env: Environment) -> RunnerPayload:
        """
        apply one time step of the update functions
        :return: the RunnerPayload with SimulationState and update functions (SimulationUpdateFunction) updated
        """
        return ft.reduce(
            lambda acc, fn: acc.apply_fn(fn, env),
            self.f,
            self._replace(f=())
        )