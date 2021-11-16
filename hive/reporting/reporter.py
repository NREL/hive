from __future__ import annotations

from immutables import Map
from pandas import DataFrame
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple

from hive.reporting.report_type import ReportType
from hive.reporting.handler.stats_handler import StatsHandler
from hive.reporting.handler.time_step_stats_handler import TimeStepStatsHandler

if TYPE_CHECKING:
    from hive.model.membership import MembershipId
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.handler import Handler
    from hive.config.global_config import GlobalConfig


class Report(NamedTuple):
    report_type: ReportType
    report: Dict[str, str]

    def as_json(self) -> Dict[str, str]:
        out = {str(k): str(v) for k, v in self.report.items()}
        out['report_type'] = self.report_type.name.lower()
        return out


class Reporter:
    """
    A class that generates reports for the simulation.
    """

    def __init__(self):
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
        for handler in self.handlers:
            handler.handle(self.reports, runner_payload)

        self.reports = []

    def file_report(self, report: Report):
        """
        files a single report to be handled later.


        :param report:
        :return:
        """
        self.reports.append(report)

    def get_summary_stats(self, rp: RunnerPayload) -> Optional[Dict]:
        """
        if a summary StatsHandler exists, return the final report from the collection of statistics
        :return: the stats Dictionary, or, None
        """
        final_report = None
        for handler in self.handlers:
            if isinstance(handler, StatsHandler):
                final_report = handler.get_stats(rp)
        return final_report

    def get_time_step_stats(self) -> Tuple[Optional[DataFrame], Optional[Map[MembershipId, DataFrame]]]:
        """
        if a TimeStepStatsHandler exists, return the time step stats DataFrame and the fleet time step stats DataFrames
        :return: the time step stats DataFrame and the fleet time step stats collection of DataFrames if they exist
        """
        time_step_stats, fleet_time_step_stats = None, None
        for handler in self.handlers:
            if isinstance(handler, TimeStepStatsHandler):
                time_step_stats = handler.get_time_step_stats()
                fleet_time_step_stats = handler.get_fleet_time_step_stats()
        return time_step_stats, fleet_time_step_stats

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        for handler in self.handlers:
            handler.close(runner_payload)
