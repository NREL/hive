from __future__ import annotations

from typing import Dict

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

    def __init__(self, io: IO, sim_output_dir: str):

        run_formatter = logging.Formatter("[%(levelname)s] - %(message)s")
        error_formatter = logging.Formatter("[%(levelname)s] - %(message)s")
        sim_formatter = logging.Formatter("%(message)s")

        run_logger = logging.getLogger(io.run_log_file)
        run_logger.setLevel(logging.INFO)

        run_fh = logging.FileHandler(os.path.join(sim_output_dir, io.run_log_file))
        run_fh.setFormatter(run_formatter)
        run_logger.addHandler(run_fh)

        run_ch = logging.StreamHandler()
        run_ch.setFormatter(run_formatter)
        run_logger.addHandler(run_ch)

        self.run_logger = run_logger

        sim_logger = logging.getLogger(io.sim_log_file)
        sim_logger.setLevel(logging.INFO)

        sim_fh = logging.FileHandler(os.path.join(sim_output_dir, io.sim_log_file))
        sim_fh.setFormatter(sim_formatter)
        sim_logger.addHandler(sim_fh)

        self.sim_logger = sim_logger

        error_logger = logging.getLogger(io.error_log_file)
        error_logger.setLevel(logging.ERROR)

        error_fh = logging.FileHandler(os.path.join(sim_output_dir, io.error_log_file))
        error_fh.setFormatter(error_formatter)
        error_logger.addHandler(error_fh)

        error_ch = logging.StreamHandler()
        error_ch.setFormatter(error_formatter)
        error_logger.addHandler(error_ch)

        self.error_logger = error_logger

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

    def sim_report(self, report: Dict):
        entry = json.dumps(report, default=str)
        self.sim_logger.info(entry)
