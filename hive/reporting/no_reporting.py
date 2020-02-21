from hive.reporting.reporter import Reporter


class NoReporting(Reporter):

    def log_sim_state(self,
                      sim_state: 'SimulationState',
                      ):
        pass
