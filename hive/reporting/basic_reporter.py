from __future__ import annotations

import json
import logging
import os

from hive.reporting.reporter import Reporter
from hive.config import IO

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

    def _report_entities(self, entities, sim_time, report_type):
        for e in entities:
            log_dict = e._asdict()
            log_dict['sim_time'] = sim_time
            log_dict['report_type'] = report_type
            entry = json.dumps(log_dict, default=str)
            self.sim_log_file.write(entry + '\n')

    def _report_vehicles(self, vehicles, sim_time):
        for v in vehicles:
            log_dict = v._asdict()
            log_dict['sim_time'] = sim_time
            log_dict['report_type'] = 'vehicle_report'
            log_dict['vehicle_state'] = v.vehicle_state.__class__.__name__
            entry = json.dumps(log_dict, default=str)
            self.sim_log_file.write(entry + '\n')

    def log_sim_state(self, sim_state: 'SimulationState'):
        if self._io.log_vehicles:
            self._report_vehicles(
                vehicles=sim_state.vehicles.values(),
                sim_time=sim_state.sim_time,
            )
        if self._io.log_requests:
            self._report_entities(
                entities=sim_state.requests.values(),
                sim_time=sim_state.sim_time,
                report_type='request_report'
            )
        if self._io.log_stations:
            self._report_entities(
                entities=sim_state.stations.values(),
                sim_time=sim_state.sim_time,
                report_type='station_report'
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
