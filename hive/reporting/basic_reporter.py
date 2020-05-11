from __future__ import annotations

import json
import logging
import os

from hive.config.io import IO
from hive.reporting.reporter import Reporter

log = logging.getLogger(__name__)


class BasicReporter(Reporter):
    """
    A basic reporter that also tracks aggregate statistics

    :param io: io config
    """
    sim_log_file = None

    def __init__(self, io: IO, sim_output_dir: str):

        sim_log_path = os.path.join(sim_output_dir, 'sim.log')
        self.sim_log_file = open(sim_log_path, 'a')

        self._io = io
        
    @staticmethod
    def request_asdict(request) -> dict:
        out_dict = request._asdict()

        # deconstruct origin_link
        out_dict['origin_link_id'] = request.origin_link.link_id
        out_dict['origin_geoid'] = request.origin_link.start
        del(out_dict['origin_link'])

        # deconstruct destination_link
        out_dict['destination_link_id'] = request.destination_link.link_id
        out_dict['destination_geoid'] = request.destination_link.start
        del(out_dict['destination_link'])

        return out_dict

    @staticmethod
    def vehicle_asdict(vehicle) -> dict:
        out_dict = vehicle._asdict()
        out_dict['vehicle_state'] = vehicle.vehicle_state.__class__.__name__

        # deconstruct energy source
        for key, val in vehicle.energy_source._asdict().items():
            new_key = 'energy_source_' + key
            out_dict[new_key] = val
        del (out_dict['energy_source'])

        # deconstruct link
        for key, val in vehicle.link._asdict().items():
            new_key = 'link_' + key
            out_dict[new_key] = val
        del (out_dict['link'])

        return out_dict

    @staticmethod
    def station_asdict(station) -> dict:
        out_dict = station._asdict()

        # deconstruct origin_link
        out_dict['link_id'] = station.link.link_id
        out_dict['geoid'] = station.link.start
        del (out_dict['link'])

        # deconstruct total_charges
        for key, val in station.total_chargers.items():
            new_key = 'total_chargers_' + key.name
            out_dict[new_key] = val
        del (out_dict['total_chargers'])

        # deconstruct available_charges
        for key, val in station.available_chargers.items():
            new_key = 'available_chargers_' + key.name
            out_dict[new_key] = val
        del (out_dict['available_chargers'])

        # deconstruct charger_prices
        for key, val in station.charger_prices_per_kwh.items():
            new_key = 'charger_prices_' + key.name
            out_dict[new_key] = val
        del (out_dict['charger_prices_per_kwh'])

        return out_dict

    def _report_entities(self, entities, asdict, sim_time, report_type):
        for e in entities:
            log_dict = asdict(e)
            log_dict['sim_time'] = sim_time
            log_dict['report_type'] = report_type
            entry = json.dumps(log_dict, default=str)
            self.sim_log_file.write(entry + '\n')

    def log_sim_state(self, sim_state: 'SimulationState'):
        if self._io.log_vehicles:
            self._report_entities(
                entities=sim_state.vehicles.values(),
                asdict=self.vehicle_asdict,
                sim_time=sim_state.sim_time,
                report_type='vehicle_report',
            )
        if self._io.log_requests:
            self._report_entities(
                entities=sim_state.requests.values(),
                asdict=self.request_asdict,
                sim_time=sim_state.sim_time,
                report_type='request_report',
            )
        if self._io.log_stations:
            self._report_entities(
                entities=sim_state.stations.values(),
                asdict=self.station_asdict,
                sim_time=sim_state.sim_time,
                report_type='station_report',
            )

    def sim_report(self, report: dict):
        if 'report_type' not in report:
            log.warning(f'must specify report_type in report, not recording report {report}')
        elif not self._io.log_dispatcher and report['report_type'] == 'dispatcher':
            return
        elif not self._io.log_requests and 'request' in report['report_type']:
            return
        else:
            entry = json.dumps(report, default=str)
            self.sim_log_file.write(entry + '\n')
