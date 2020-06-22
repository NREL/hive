from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, NamedTuple

if TYPE_CHECKING:
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.handler import Handler
    from hive.config.global_config import GlobalConfig


class ReportType(Enum):
    """
    A strict set of report types
    """
    STATION_STATE = 1
    VEHICLE_STATE = 2
    ADD_REQUEST_EVENT = 3
    PICKUP_REQUEST_EVENT = 4
    CANCEL_REQUEST_EVENT = 5
    INSTRUCTION = 6
    VEHICLE_CHARGE_EVENT = 7
    VEHICLE_MOVE_EVENT = 8

    @classmethod
    def from_string(cls, s: str) -> ReportType:
        values = {
            "station_state": cls.STATION_STATE,
            "vehicle_state": cls.VEHICLE_STATE,
            "add_request_event": cls.ADD_REQUEST_EVENT,
            "pickup_request_event": cls.PICKUP_REQUEST_EVENT,
            "cancel_request_event": cls.CANCEL_REQUEST_EVENT,
            "instruction": cls.INSTRUCTION,
            "vehicle_charge_event": cls.VEHICLE_CHARGE_EVENT,
            "vehicle_move_event": cls.VEHICLE_MOVE_EVENT,
        }
        try:
            return values[s]
        except KeyError:
            raise KeyError(f"{s} not a valid report type.")


class Report(NamedTuple):
    report_type: ReportType
    report: Dict[str, str]

    def as_json(self) -> Dict[str, str]:
        out = self.report
        out['report_type'] = self.report_type.name.lower()
        return out


class Reporter:
    """
    A class that generates reports for the simulation.
    """

    def __init__(self, config: GlobalConfig):
        self.config = config
        self.reports: List[Report] = []
        self.handlers: List[Handler] = []

    def add_handler(self, handler: Handler):
        self.handlers.append(handler)

    def flush(self, runner_payload: RunnerPayload):
        """
        called at each sim step.

        :param runner_payload: The runner payload.
        :return: Does not return a value.
        """

        # TODO: This is too fragile. We should think about introducing a sim step parameter.
        if runner_payload.s.sim_time % self.config.log_period_seconds != 0:
            return

        for handler in self.handlers:
            handler.handle(self.reports, runner_payload)

        self.reports = []

    def file_report(self, report: Report):
        """
        files a single report to be handled later.

        :param report:
        :return:
        """
        if report.report_type in self.config.log_sim_config:
            self.reports.append(report)

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        for handler in self.handlers:
            handler.close(runner_payload)
