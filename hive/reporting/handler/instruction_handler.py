from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, List

from hive.reporting import vehicle_event_ops
from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from hive.config.global_config import GlobalConfig
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report

log = logging.getLogger(__name__)


class InstructionHandler(Handler):
    """
    handles events and appends them to the event.log output file based on global logging settings
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: Path):

        log_path = scenario_output_directory / 'instruction.log'
        self.log_file = open(log_path, 'a')

        self.global_config = global_config

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):

        for report in reports:
            if report.report_type == ReportType.INSTRUCTION and ReportType.INSTRUCTION in self.global_config.log_sim_config:
                report_json = report.as_json()
                entry = json.dumps(report_json, default=str)
                self.log_file.write(entry + '\n')

    def close(self, runner_payload: RunnerPayload):
        self.log_file.close()
        self.log_file = None
