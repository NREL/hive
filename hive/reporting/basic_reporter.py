from __future__ import annotations

from typing import Tuple

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
        def _setup_logger(name, log_file, level=logging.INFO):
            logger = logging.getLogger(name)
            logger.setLevel(level)

            fh = logging.FileHandler(log_file)
            logger.addHandler(fh)

            return logger

        self.run_logger = _setup_logger(name=io.run_log_file,
                                        log_file=os.path.join(sim_output_dir, io.run_log_file))

        self.sim_logger = _setup_logger(name=io.sim_log_file,
                                        log_file=os.path.join(sim_output_dir, io.sim_log_file))

        self.error_logger = _setup_logger(name=io.error_log_file,
                                          log_file=os.path.join(sim_output_dir, io.error_log_file))

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
