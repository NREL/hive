from typing import List

import pandas as pd
from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.runner import RunnerPayload
from hive.util import SimulationStateError


class VehicleChargeEventsHandler(Handler):
    """
    allows grid co-simulation to observe the charging events within a time delta of hive
    """


    def __init__(self) -> None:
        self.prototype = {'vehicle_id': [], 'sim_time_start': [], 'sim_time_end': [], 'energy': [], 'units': []}
        self.events = self.prototype.copy()

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        for report in reports:
            if report.report_type == ReportType.VEHICLE_CHARGE_EVENT:
                try:
                    self.events['vehicle_id'].append(report.report['vehicle_id'])
                    self.events['sim_time_start'].append(report.report['sim_time_start'])
                    self.events['sim_time_end'].append(report.report['sim_time_end'])
                    self.events['energy'].append(report.report['energy'])
                    self.events['units'].append(report.report['energy_units'])
                except KeyError as e:
                    raise SimulationStateError(f'unable to parse charge event from report {report}, missing entry for {e}')

    def get_events(self):
        """
        grabs the events as a pandas dataframe
        :return: a pandas dataframe containing charge events
        """
        df = pd.DataFrame(data=self.events)
        return df

    def clear(self):
        """
        clears the stored events
        :return:
        """
        self.events = self.prototype.copy()

    def close(self, runner_payload: RunnerPayload):
        pass

