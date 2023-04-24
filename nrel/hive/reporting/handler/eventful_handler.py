from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

from nrel.hive.reporting import vehicle_event_ops
from nrel.hive.reporting.handler.handler import Handler
from nrel.hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from nrel.hive.config.global_config import GlobalConfig
    from nrel.hive.runner.runner_payload import RunnerPayload
    from nrel.hive.reporting.reporter import Report

log = logging.getLogger(__name__)


class EventfulHandler(Handler):
    """
    handles events and appends them to the event.log output file based on global logging settings
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: Path):
        log_path = scenario_output_directory / "event.log"
        self.log_file = open(log_path, "a")

        self.global_config = global_config

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        sim_state = runner_payload.s

        reports_not_instructions = tuple(
            filter(lambda r: r.report_type != ReportType.INSTRUCTION, reports)
        )

        # station load events, written with reference to a specific station, take the sum of
        # charge events over a time step associated with a single station
        if ReportType.STATION_LOAD_EVENT in self.global_config.log_sim_config:
            station_load_reports = vehicle_event_ops.construct_station_load_events(
                reports_not_instructions, sim_state
            )
            for report in station_load_reports:
                entry = json.dumps(report.as_json(), default=str)
                self.log_file.write(entry + "\n")

        for report in reports_not_instructions:
            if report.report_type in self.global_config.log_sim_config:
                report_json = report.as_json()
                entry = json.dumps(report_json, default=str)
                self.log_file.write(entry + "\n")

    def close(self, runner_payload: RunnerPayload):
        self.log_file.close()
