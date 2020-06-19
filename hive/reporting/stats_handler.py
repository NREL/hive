from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from typing import TYPE_CHECKING, List

import numpy as np

from hive.reporting.handler import Handler
from hive.reporting.reporter import ReportType

if TYPE_CHECKING:
    from hive.reporting.reporter import Report
    from hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)


@dataclass
class Stats:
    state_count: Counter = field(default_factory=lambda: Counter())
    vkt: Counter = field(default_factory=lambda: Counter())

    requests: int = 0
    cancelled_reqeusts: int = 0

    mean_final_soc: float = 0

    station_revenue: float = 0
    fleet_revenue: float = 0

    def log(self):
        log.info(f"{self.mean_final_soc * 100:.2f} % \t Mean Final SOC".expandtabs(15))
        log.info(
            f"{(1 - (self.cancelled_reqeusts / self.requests)) * 100:.2f} % \t Requests Served"
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
                    lambda r: r.report_type == ReportType.VEHICLE_MOVE_EVENT,
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
        self.stats.requests += c[ReportType.ADD_REQUEST]
        self.stats.cancelled_reqeusts += c[ReportType.CANCEL_REQUEST]

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        sim_state = runner_payload.s
        env = runner_payload.e

        self.stats.mean_final_soc = np.mean([
            env.mechatronics.get(v.mechatronics_id).battery_soc(v) for v in sim_state.vehicles.values()
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
