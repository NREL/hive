from typing import Tuple, TYPE_CHECKING

from hive.reporting import Reporter


class NoReporting(Reporter):

    def report(self, sim_state: 'SimulationState', reports: Tuple[str, ...]):
        pass
