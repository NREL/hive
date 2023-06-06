from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from statistics import mean
from typing import TYPE_CHECKING, Dict, Any
from nrel.hive.model.energy.energytype import EnergyType

if TYPE_CHECKING:
    from nrel.hive.runner.runner_payload import RunnerPayload

log = logging.getLogger(__name__)

from rich.table import Table
from rich.console import Console


@dataclass
class SummaryStats:
    state_count: Counter = field(default_factory=lambda: Counter())
    vkt: Counter = field(default_factory=lambda: Counter())

    requests: int = 0
    cancelled_requests: int = 0

    mean_final_soc: float = 0

    station_revenue: float = 0
    fleet_revenue: float = 0

    total_vkwh_expended: float = 0
    total_vgge_expended: float = 0

    total_skwh_dispensed: float = 0
    total_sgge_dispensed: float = 0

    def compile_stats(self, rp: RunnerPayload) -> Dict[str, Any]:
        """
        computes all stats based on values accumulated throughout this run
        :return: a dictionary with stat values by key
        """

        sim_state = rp.s
        env = rp.e

        self.mean_final_soc = mean(
            [
                env.mechatronics[v.mechatronics_id].fuel_source_soc(v)
                for v in sim_state.get_vehicles()
            ]
        )

        self.station_revenue = reduce(
            lambda income, station: income + station.balance,
            sim_state.get_stations(),
            0.0,
        )

        self.fleet_revenue = reduce(
            lambda income, vehicle: income + vehicle.balance,
            sim_state.get_vehicles(),
            0.0,
        )

        if self.requests > 0:
            requests_served_percent = 1 - (self.cancelled_requests / self.requests)
        else:
            requests_served_percent = 0.0

        total_state_count = sum(self.state_count.values())
        total_vkt = sum(self.vkt.values())
        vehicle_state_output = {}
        vehicle_states_observed = set(self.state_count.keys()).union(self.vkt.keys())
        for v in vehicle_states_observed:
            state_count = self.state_count.get(v)
            if state_count is None:
                observed_pct = 0.0
            else:
                observed_pct = state_count / total_state_count
            vkt = self.vkt.get(v, 0)
            data = {"observed_percent": observed_pct, "vkt": vkt}
            vehicle_state_output.update({v: data})

        total_vkwh_expended = 0.0
        total_vgge_expended = 0.0
        for vehicle in rp.s.get_vehicles():
            total_vkwh_expended += vehicle.energy_expended.get(EnergyType.ELECTRIC, 0.0)
            total_vgge_expended += vehicle.energy_expended.get(EnergyType.GASOLINE, 0.0)

        self.total_vkwh_expended = total_vkwh_expended
        self.total_vgge_expended = total_vgge_expended

        total_skwh_dispensed = 0.0
        total_sgge_dispensed = 0.0
        for station in rp.s.get_stations():
            total_skwh_dispensed += station.energy_dispensed.get(EnergyType.ELECTRIC, 0.0)
            total_sgge_dispensed += station.energy_dispensed.get(EnergyType.GASOLINE, 0.0)

        self.total_skwh_dispensed = total_skwh_dispensed
        self.total_sgge_dispensed = total_sgge_dispensed

        output = {
            "mean_final_soc": self.mean_final_soc,
            "requests_served_percent": requests_served_percent,
            "vehicle_state": vehicle_state_output,
            "total_vkt": total_vkt,
            "total_kwh_expended": total_vkwh_expended,
            "total_gge_expended": total_vgge_expended,
            "total_kwh_dispensed": total_skwh_dispensed,
            "total_gge_dispensed": total_sgge_dispensed,
            "station_revenue_dollars": self.station_revenue,
            "fleet_revenue_dollars": self.fleet_revenue,
            "final_vehicle_count": len(sim_state.vehicles),
        }

        return output

    def log(self):
        table = Table(title="Summary Stats")
        table.add_column("Stat")
        table.add_column("Value")

        table.add_row("Mean Final SOC", f"{round(self.mean_final_soc * 100, 2)}%")
        requests_served_percent = (
            (1 - (self.cancelled_requests / self.requests)) * 100 if self.requests > 0 else 0
        )
        table.add_row("Requests Served", f"{round(requests_served_percent, 2)}%")
        log.info(f"{requests_served_percent:.2f} % \t Requests Served".expandtabs(15))

        total_state_count = sum(self.state_count.values())
        for s, v in self.state_count.items():
            table.add_row(f"Time in State {s}", f"{round(v / total_state_count * 100, 2)}%")

        total_vkt = sum(self.vkt.values())
        table.add_row("Total Kilometers Traveled", f"{round(total_vkt, 2)} km")
        for s, v in self.vkt.items():
            table.add_row(f"Kilometers Traveled in State {s}", f"{round(v, 2)} km")

        table.add_row("Total kWh Expended By Vehicles", f"{round(self.total_vkwh_expended, 2)} kWh")
        table.add_row(
            "Total Gasoline Expended By Vehicles", f"{round(self.total_vgge_expended, 2)} Gal"
        )

        table.add_row(
            "Total kWh Dispensed By Stations", f"{round(self.total_skwh_dispensed, 2)} kWh"
        )
        table.add_row(
            "Total Gasoline Dispensed By Stations", f"{round(self.total_sgge_dispensed, 2)} Gal"
        )

        table.add_row("Station Revenue", f"$ {round(self.station_revenue, 2)}")
        table.add_row("Fleet Revenue", f"$ {round(self.fleet_revenue, 2)}")

        console = Console()
        console.print(table)
