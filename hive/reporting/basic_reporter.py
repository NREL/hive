from __future__ import annotations

import json
import logging
import os

from hive.reporting.reporter import Reporter
from hive.config import IO


class BasicReporter(Reporter):
    """
    A class that generates very detailed reports for the simulation.

    :param io: io config
    """
    sim_logger = None

    def __init__(self, io: IO, sim_output_dir: str):

        sim_formatter = logging.Formatter("%(message)s")

        sim_logger = logging.getLogger(io.sim_log_file)
        sim_logger.setLevel(logging.INFO)

        sim_fh = logging.FileHandler(os.path.join(sim_output_dir, io.sim_log_file))
        sim_fh.setFormatter(sim_formatter)
        sim_logger.addHandler(sim_fh)

        self.sim_logger = sim_logger

        self._log_vehicles = io.log_vehicles
        self._log_requests = io.log_requests
        self._log_stations = io.log_stations
        self._log_dispatcher = io.log_dispatcher
        self._log_manager = io.log_manager

    def _report_entities(self, entities, sim_time):
        for e in entities:
            log_dict = e._asdict()
            log_dict['sim_time'] = sim_time
            entry = json.dumps(log_dict, default=str)
            self.sim_logger.info(entry)

    def log_sim_state(self, sim_state: 'SimulationState'):

        if self._log_vehicles:
            self._report_entities(
                entities=sim_state.vehicles.values(),
                sim_time=sim_state.sim_time
            )
        if self._log_requests:
            self._report_entities(
                entities=sim_state.requests.values(),
                sim_time=sim_state.sim_time
            )
        if self._log_stations:
            self._report_entities(
                entities=sim_state.stations.values(),
                sim_time=sim_state.sim_time
            )

    def sim_report(self, report: dict):
        entry = json.dumps(report, default=str)
        self.sim_logger.info(entry)
