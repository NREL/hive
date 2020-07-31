from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, List

from hive.model.vehicle import Vehicle
from hive.reporting import vehicle_event_ops
from hive.reporting.handler import Handler
from hive.reporting.reporter import ReportType

if TYPE_CHECKING:
    from hive.config.global_config import GlobalConfig
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report
    from hive.model.station import Station

log = logging.getLogger(__name__)


class SimLogHandler(Handler):
    """
    Generates the sim.log output file

    :param global_config: global project configuration
    :param scenario_output_directory: the output directory for this scenario
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: str):

        sim_log_path = os.path.join(scenario_output_directory, 'sim.log')
        self.sim_log_file = open(sim_log_path, 'a')

        self.global_config = global_config

    @staticmethod
    def vehicle_asdict(vehicle: Vehicle) -> dict:
        output = {
            'vehicle_id': vehicle.id,
            'vehicle_state': vehicle.vehicle_state.__class__.__name__,
            'balance': vehicle.balance,
            'distance_traveled_km': vehicle.distance_traveled_km,
        }

        # deconstruct energy source
        for key, val in vehicle.energy.items():
            new_key = 'energy_' + key.name
            output[new_key] = val
        # del (output['energy'])

        # deconstruct link
        for key, val in vehicle.link._asdict().items():
            new_key = 'link_' + key
            output[new_key] = val
        # del (output['link'])

        return output

    @staticmethod
    def station_asdict(station: Station) -> dict:
        out_dict = station._asdict()
        del(out_dict["id"])

        out_dict["station_id"] = station.id

        # deconstruct origin_link
        out_dict['link_id'] = station.link.link_id
        out_dict['geoid'] = station.link.start
        del (out_dict['link'])

        # deconstruct total_charges
        for key, val in station.total_chargers.items():
            new_key = 'total_chargers_' + key
            out_dict[new_key] = val
        del (out_dict['total_chargers'])

        # deconstruct available_charges
        for key, val in station.available_chargers.items():
            new_key = 'available_chargers_' + key
            out_dict[new_key] = val
        del (out_dict['available_chargers'])

        # deconstruct charger_prices
        for key, val in station.charger_prices_per_kwh.items():
            new_key = 'charger_prices_' + key
            out_dict[new_key] = val
        del (out_dict['charger_prices_per_kwh'])

        return out_dict

    def _report_entities(self, entities, asdict, sim_time, report_type):
        for e in entities:
            log_dict = asdict(e)
            log_dict['sim_time'] = sim_time
            log_dict['report_type'] = report_type.name
            entry = json.dumps(log_dict, default=str)
            self.sim_log_file.write(entry + '\n')

    def handle(
            self,
            reports: List[Report],
            runner_payload: RunnerPayload,
    ):
        sim_state = runner_payload.s
        if ReportType.VEHICLE_STATE in self.global_config.log_sim_config:
            self._report_entities(
                entities=sim_state.vehicles.values(),
                asdict=self.vehicle_asdict,
                sim_time=sim_state.sim_time,
                report_type=ReportType.VEHICLE_STATE,
            )

        if ReportType.STATION_STATE in self.global_config.log_sim_config:
            self._report_entities(
                entities=sim_state.stations.values(),
                asdict=self.station_asdict,
                sim_time=sim_state.sim_time,
                report_type=ReportType.STATION_STATE,
            )

        if runner_payload.e.config.global_config.log_station_load:
            station_load_reports = vehicle_event_ops.construct_station_load_events(tuple(reports), sim_state)
            for report in station_load_reports:
                entry = json.dumps(report.as_json(), default=str)
                self.sim_log_file.write(entry + '\n')

        for report in reports:
            entry = json.dumps(report.as_json(), default=str)
            self.sim_log_file.write(entry + '\n')

    def close(self, runner_payload: RunnerPayload):
        self.sim_log_file.close()
