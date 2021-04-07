from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from typing import TYPE_CHECKING, Dict

import numpy as np

if TYPE_CHECKING:
    from hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)


@dataclass
class SummaryStats:
    state_count: Counter = field(default_factory=lambda: Counter())
    vkt: Counter = field(default_factory=lambda: Counter())

    requests: int = 0
    cancelled_requests: int = 0

    mean_final_soc: float = 0

    station_revenue: float = 0
    fleet_revenue: float = 0

    def compile_stats(self, rp: RunnerPayload) -> Dict[str, float]:
        """
        computes all stats based on values accumulated throughout this run
        :return: a dictionary with stat values by key
        """

        sim_state = rp.s
        env = rp.e

        self.mean_final_soc = np.mean([
            env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in sim_state.vehicles.values()
        ])

        self.station_revenue = reduce(
            lambda income, station: income + station.balance,
            sim_state.stations.values(),
            0.0
        )

        self.fleet_revenue = reduce(
            lambda income, vehicle: income + vehicle.balance,
            sim_state.vehicles.values(),
            0.0
        )

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
            "fleet_revenue_dollars": self.fleet_revenue,
            "final_vehicle_count": len(sim_state.vehicles)
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
