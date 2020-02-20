from typing import Tuple, TYPE_CHECKING

from hive.reporting.reporter import Reporter
# from hive.state.simulation_state import SimulationState


class NoReporting(Reporter):

    def report(self, sim_state: 'SimulationState', reports: Tuple[str, ...]):
        pass

    def single_report(self, report: str):
        pass
