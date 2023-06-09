import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from nrel.hive.config.global_config import GlobalConfig
from nrel.hive.model.station.station import Station
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.reporting.handler.handler import Handler
from nrel.hive.reporting.report_type import ReportType
from nrel.hive.reporting.reporter import Report
from nrel.hive.runner import RunnerPayload


class StatefulHandler(Handler):
    """
    prints the state of entities in the simulation to the state.log output file based on global logging settings
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: Path):
        log_path = scenario_output_directory / "state.log"
        self.log_file = open(log_path, "a")

        self.global_config = global_config

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        reports the driver, vehicle and station state at the current time for all
        entities, written to state.log.

        :param reports: ignored

        :param runner_payload: provides the current simulation state
        """
        sim_state = runner_payload.s
        if ReportType.DRIVER_STATE in self.global_config.log_sim_config:
            self._report_entities(
                entities=sim_state.get_vehicles(),
                asdict=self.driver_asdict,
                sim_time=sim_state.sim_time,
                report_type=ReportType.DRIVER_STATE,
            )

        if ReportType.VEHICLE_STATE in self.global_config.log_sim_config:
            self._report_entities(
                entities=sim_state.get_vehicles(),
                asdict=self.vehicle_asdict,
                sim_time=sim_state.sim_time,
                report_type=ReportType.VEHICLE_STATE,
            )

        if ReportType.STATION_STATE in self.global_config.log_sim_config:
            self._report_entities(
                entities=sim_state.get_stations(),
                asdict=self.station_asdict,
                sim_time=sim_state.sim_time,
                report_type=ReportType.STATION_STATE,
            )

    def close(self, runner_payload: RunnerPayload):
        self.log_file.close()

    @staticmethod
    def driver_asdict(vehicle: Vehicle) -> dict:
        output = {
            "vehicle_id": vehicle.id,
            "driver_state": vehicle.driver_state.__class__.__name__,
            "schedule_id": vehicle.driver_state.schedule_id
            if vehicle.driver_state.schedule_id
            else "",
            "available": vehicle.driver_state.available,
        }

        return output

    @staticmethod
    def vehicle_asdict(vehicle: Vehicle) -> dict:
        output = {
            "vehicle_id": vehicle.id,
            "memberships": str(vehicle.membership),
            "vehicle_state": vehicle.vehicle_state.__class__.__name__,
            "balance": vehicle.balance,
            "distance_traveled_km": vehicle.distance_traveled_km,
        }

        # deconstruct energy source
        for energy_type, energy_val in vehicle.energy.items():
            new_key = "energy_" + energy_type.name
            output[new_key] = energy_val
        # del (output['energy'])

        # deconstruct link
        for key, val in vehicle.position._asdict().items():
            new_key = "link_" + key
            output[new_key] = val
        # del (output['link'])

        return output

    @staticmethod
    def station_asdict(station: Station) -> dict:
        out_dict = asdict(station)
        del out_dict["id"]
        del out_dict["state"]
        del out_dict["energy_dispensed"]

        out_dict["station_id"] = station.id
        out_dict["memberships"] = str(station.membership)

        # deconstruct origin_link
        out_dict["link_id"] = station.position.link_id
        out_dict["geoid"] = station.position.geoid
        del out_dict["position"]

        # deconstruct charger states
        for key, cs in station.state.items():
            out_dict[f"total_chargers_{key}"] = cs.total_chargers
            out_dict[f"available_chargers_{key}"] = cs.available_chargers
            out_dict[f"charger_prices_{key}"] = cs.price_per_kwh

        return out_dict

    def _report_entities(self, entities, asdict, sim_time, report_type):
        for e in entities:
            log_dict = asdict(e)
            log_dict["sim_time"] = str(sim_time)
            log_dict["report_type"] = report_type.name
            entry = json.dumps(log_dict, default=str)
            self.log_file.write(entry + "\n")
