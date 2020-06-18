from __future__ import annotations

import logging

from dataclasses import dataclass
from collections import Counter
from typing import TYPE_CHECKING, List

import numpy as np

from hive.reporting.handler import Handler

if TYPE_CHECKING:
    from hive.reporting.reporter import Report
    from hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)


@dataclass
class Stats:
    total_vkt: float = 0
    total_deadhead_vkt: float = 0

    requests: int = 0
    cancelled_reqeusts: int = 0


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
        move_events = list(filter(lambda r: r['report_type'] == 'vehicle_move_event', reports))

        step_vkt = sum(map(lambda me: me['distance_km'], move_events))
        self.stats.total_vkt += step_vkt

        trip_vkt = sum(map(
            lambda me: me['distance_km'],
            filter(
                lambda me: me['vehicle_state'] == 'ServicingTrip',
                move_events
            )
        ))
        self.stats.total_deadhead_vkt += (step_vkt - trip_vkt)

        c = Counter(map(lambda r: r['report_type'], reports))
        self.stats.requests += c['add_request']
        self.stats.cancelled_reqeusts += c['cancel_request']

    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
        sim_state = runner_payload.s
        env = runner_payload.e

        mean_final_soc = np.mean([
            env.mechatronics.get(v.mechatronics_id).battery_soc(v) for v in sim_state.vehicles.values()
        ])

        log.info(f"total_vkt: {round(self.stats.total_vkt, 2)} kilometers")
        log.info(f"total_deadhead_vkt: {round(self.stats.total_deadhead_vkt, 2)} kilometers")
        log.info(f"mean final soc: {round(float(mean_final_soc * 100), 2)} %")
        log.info(f"requests served: {round(1 - (self.stats.cancelled_reqeusts / self.stats.requests) * 100, 2)} %")
