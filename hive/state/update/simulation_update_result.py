from __future__ import annotations

from typing import NamedTuple, Tuple, Optional

from hive.state.simulation_state import SimulationState


class SimulationUpdateResult(NamedTuple):
    simulation_state: SimulationState
    reports: Tuple[str, ...] = ()

    def add_report(self, report: str) -> SimulationUpdateResult:
        return self._replace(reports=(report,) + self.reports)

    def update_sim(self, sim: SimulationState, report: Optional[str] = None) -> SimulationUpdateResult:
        if report is not None:
            return self._replace(
                simulation_state=sim,
                reports=(report,) + self.reports
            )
        else:
            return self._replace(
                simulation_state=sim
            )