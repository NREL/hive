from __future__ import annotations

import json

import logging
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict

import numpy as np

from hive.reporting.handler.handler import Handler
from hive.reporting.handler.summary_stats import SummaryStats
from hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from hive.reporting.reporter import Report
    from hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)


class StatsHandler(Handler):
    """
    The StatsHandler compiles various simulation statistics and stores them.
    """

    def __init__(self):
        self.stats = SummaryStats()

    def get_stats(self, rp: RunnerPayload) -> Dict:
        """
        special output specifically for the StatsHandler which produces the
        summary file output
        :return: the compiled stats for this simulation run
        """
        return self.stats.compile_stats(rp)

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        called at each log step.


        :param reports:

        :param runner_payload
        :return:
        """

        # update the proportion of time spent by vehicles in each vehicle state
        sim_state = runner_payload.s
        state_counts = Counter(
            map(
                lambda v: v.vehicle_state.__class__.__name__,
                sim_state.get_vehicles()
            )
        )
        self.stats.state_count += state_counts

        # capture the distance traveled in move states
        move_events = list(
            filter(
                lambda r: r.report_type == ReportType.VEHICLE_MOVE_EVENT,
                reports
            )
        )
        for me in move_events:
            self.stats.vkt[me.report['vehicle_state']] += me.report['distance_km']

        # count any requests and cancelled requests
        c = Counter(map(lambda r: r.report_type, reports))
        self.stats.requests += c[ReportType.ADD_REQUEST_EVENT]
        self.stats.cancelled_requests += c[ReportType.CANCEL_REQUEST_EVENT]

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        output = self.stats.compile_stats(runner_payload)
        self.stats.log()
        output_path = Path(runner_payload.e.config.scenario_output_directory).joinpath("summary_stats.json")
        with output_path.open(mode="w") as f:
            json.dump(output, f, indent=4)
            log.info(f"summary stats written to {output_path}")

