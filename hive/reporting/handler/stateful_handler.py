import json
import os
from typing import List

from hive.config.global_config import GlobalConfig
from hive.model.station import Station
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.runner import RunnerPayload


class StatefulHandler(Handler):
    """
    prints the state of entities in the simulation to the state.log output file based on global logging settings
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: str):

        log_path = os.path.join(scenario_output_directory, 'state.log')
        self.log_file = open(log_path, 'a')

        self.global_config = global_config

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        reports the vehicle and station state at the current time, written
        to state.log.

        :param reports: ignored
        :param runner_payload: provides the current simulation state
        """
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

    def close(self, runner_payload: RunnerPayload):
        self.log_file.close()

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
            self.log_file.write(entry + '\n')