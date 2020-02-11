from __future__ import annotations

from typing import NamedTuple, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.runner.environment import Environment
    from hive.state.simulation_state import SimulationState
    from hive.state.update import Update


class RunnerPayload(NamedTuple):
    """
    Holds the simulation state, dispatcher and reports for the simulation run.

    :param s: the simulation state
    :type s: :py:obj:`SimulationState`
    :param e: the environmental assets for this simulation
    :type e: :py:obj:`Environment`
    :param u: the updates we need to apply during each sim step
    :type u: :py:obj:`Update`
    :param r: any reports generated for a timestep
    :type r: :py:obj:`Tuple[str, ...]`
    """
    s: SimulationState
    e: Environment
    u: Update
    r: Tuple[str, ...] = ()

    def add_reports(self, reports: Tuple[str, ...]) -> RunnerPayload:
        return self._replace(r=self.r + reports)

    def clear_reports(self) -> RunnerPayload:
        """
        in the future, we just want to send reports as soon as we have them. but, the
        current design has the reports stored back into the RunnerPayload temporarily.
        after they are reported, this clears them (preventing re-reporting them at t+1).
        :return: this payload with no reports
        """
        return self._replace(r=())
