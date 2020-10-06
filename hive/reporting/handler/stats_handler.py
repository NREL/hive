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
from hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from hive.reporting.reporter import Report
    from hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)


@dataclass
class Stats:
    state_count: Counter = field(default_factory=lambda: Counter())
    vkt: Counter = field(default_factory=lambda: Counter())

    requests: int = 0
    cancelled_requests: int = 0

    mean_final_soc: float = 0

    station_revenue: float = 0
    fleet_revenue: float = 0

    def compile_stats(self) -> Dict[str, float]:
        """
        computes all stats based on values accumulated throughout this run
        :return: a dictionary with stat values by key
        """
        requests_served_percent = 1 - (self.cancelled_requests / self.requests) if self.requests > 0 else 0
        total_state_count = sum(self.state_count.values())
        total_vkt = sum(self.vkt.values())
        vehicle_state_output = {}
        vehicle_states_observed = set(self.state_count.keys()).union(self.vkt.keys())
        for v in vehicle_states_observed:
            observed_pct = self.state_count.get(v) / total_state_count if self.state_count.get(v) else 0
            vkt = self.vkt.get(v, 0)
            data = {
                "observed_percent": observed_pct,
                "vkt": vkt
            }
            vehicle_state_output.update({v: data})

        output = {
            "mean_final_soc": self.mean_final_soc,
            "requests_served_percent": requests_served_percent,
            "vehicle_state": vehicle_state_output,
            "total_vkt": total_vkt,
            "station_revenue_dollars": self.station_revenue,
            "fleet_revenue_dollars": self.fleet_revenue
        }

        return output

    def log(self):
        log.info(f"{self.mean_final_soc * 100:.2f} % \t Mean Final SOC".expandtabs(15))
        requests_served_percent = (1 - (self.cancelled_requests / self.requests)) * 100 if self.requests > 0 else 0
        log.info(
            f"{requests_served_percent:.2f} % \t Requests Served"
                .expandtabs(15)
        )

        total_state_count = sum(self.state_count.values())
        for s, v in self.state_count.items():
            log.info(f"{round(v / total_state_count * 100, 2)} % \t Time in State {s}".expandtabs(15))

        total_vkt = sum(self.vkt.values())
        log.info(f"{total_vkt:.2f} km \t Total Kilometers Traveled".expandtabs(15))
        for s, v in self.vkt.items():
            log.info(f"{v:.2f} km \t Kilometers Traveled in State {s}".expandtabs(15))

        log.info(f"$ {self.station_revenue:.2f} \t Station Revenue".expandtabs(15))
        log.info(f"$ {self.fleet_revenue:.2f} \t Fleet Revenue".expandtabs(15))


class StatsHandler(Handler):
    """
    The StatsHandler compiles various simulation statistics and stores them.
    """

    def __init__(self):
        self.stats = Stats()

    def get_stats(self) -> Dict:
        """
        special output specifically for the StatsHandler which produces the
        summary file output
        :return: the compiled stats for this simulation run
        """
        return self.stats.compile_stats()

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        called at each log step.

        :param reports:
        :param runner_payload
        :return:
        """

        state_counts = Counter(
            map(
                lambda r: r.report['vehicle_state'],
                filter(
                    lambda r: r.report_type == ReportType.VEHICLE_MOVE_EVENT or r.report_type == ReportType.VEHICLE_CHARGE_EVENT,
                    reports
                )
            )
        )

        self.stats.state_count += state_counts

        move_events = list(
            filter(
                lambda r: r.report_type == ReportType.VEHICLE_MOVE_EVENT,
                reports
            )
        )

        for me in move_events:
            self.stats.vkt[me.report['vehicle_state']] += me.report['distance_km']

        c = Counter(map(lambda r: r.report_type, reports))
        self.stats.requests += c[ReportType.ADD_REQUEST_EVENT]
        self.stats.cancelled_requests += c[ReportType.CANCEL_REQUEST_EVENT]

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        sim_state = runner_payload.s
        env = runner_payload.e

        self.stats.mean_final_soc = np.mean([
            env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in sim_state.vehicles.values()
        ])

        self.stats.station_revenue = reduce(
            lambda income, station: income + station.balance,
            sim_state.stations.values(),
            0.0
        )

        self.stats.fleet_revenue = reduce(
            lambda income, vehicle: income + vehicle.balance,
            sim_state.vehicles.values(),
            0.0
        )

        self.stats.log()
        output = self.stats.compile_stats()
        output_path = Path(runner_payload.e.config.scenario_output_directory).joinpath("summary_stats.json")
        with output_path.open(mode="w") as f:
            json.dump(output, f, indent=4)
            log.info(f"summary stats written to {output_path}")

