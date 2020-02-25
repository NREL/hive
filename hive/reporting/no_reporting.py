from hive.reporting.reporter import Reporter


class NoReporting(Reporter):

    sim_logger = None

    def log_sim_state(self, sim_state: 'SimulationState'):
        """
        Takes in a simulation state and generates reports

        :param sim_state: The simulation state.
        :return: Does not return a value.
        """
        pass

    def sim_report(self, report: dict):
        """
        Writes a single report to the simulation log.

        :param report:
        :return:
        """
        pass
