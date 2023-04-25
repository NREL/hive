from typing import List, Dict

from nrel.hive.reporting.handler.handler import Handler
from nrel.hive.reporting.report_type import ReportType
from nrel.hive.reporting.reporter import Report
from nrel.hive.runner import RunnerPayload
from nrel.hive.util import SimulationStateError


class VehicleChargeEventsHandler(Handler):
    """
    allows grid co-simulation to observe the charging events within a time delta of hive
    """

    def __init__(self) -> None:
        self.prototype: Dict[str, List] = {
            "vehicle_id": [],
            "sim_time_start": [],
            "sim_time_end": [],
            "energy": [],
            "units": [],
        }
        self.events = self.prototype.copy()

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        for report in reports:
            if report.report_type == ReportType.VEHICLE_CHARGE_EVENT:
                try:
                    self.events["vehicle_id"].append(report.report["vehicle_id"])
                    self.events["sim_time_start"].append(report.report["sim_time_start"])
                    self.events["sim_time_end"].append(report.report["sim_time_end"])
                    self.events["energy"].append(report.report["energy"])
                    self.events["units"].append(report.report["energy_units"])
                except KeyError as e:
                    raise SimulationStateError(
                        f"unable to parse charge event from report {report}, missing entry for {e}"
                    )

    def get_events(self) -> Dict[str, list]:
        """
        grabs the events as a pandas dataframe
        :return: a pandas dataframe containing charge events
        """
        return self.events

    def clear(self):
        """
        clears the stored events
        :return:
        """
        self.events = self.prototype.copy()

    def close(self, runner_payload: RunnerPayload):
        pass
