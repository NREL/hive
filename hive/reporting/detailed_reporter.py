from __future__ import annotations

from typing import Tuple

import json
import logging
import os

from hive.state.simulation_state import SimulationState
from hive.dispatcher.instruction import Instruction
from hive.reporting.reporter import Reporter
from hive.config import IO


class DetailedReporter(Reporter):
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

        if io.run_log:
            self.run_logger = _setup_logger(name=io.run_log,
                                            log_file=os.path.join(sim_output_dir, io.run_log))
        else:
            self.run_logger = None
        if io.vehicle_log:
            self.vehicle_logger = _setup_logger(name=io.vehicle_log,
                                                log_file=os.path.join(sim_output_dir, io.vehicle_log))
        else:
            self.vehicle_logger = None
        if io.request_log:
            self.request_logger = _setup_logger(name=io.request_log,
                                                log_file=os.path.join(sim_output_dir, io.request_log))
        else:
            self.request_logger = None
        if io.instruction_log:
            self.instruction_logger = _setup_logger(name=io.instruction_log,
                                                    log_file=os.path.join(sim_output_dir, io.instruction_log))
        else:
            self.instruction_logger = None

    def _report_entities(self, logger, entities, sim_time):
        if logger:
            for e in entities:
                log_dict = e._asdict()
                log_dict['sim_time'] = sim_time
                entry = json.dumps(log_dict, default=str)
                logger.info(entry)

    def report(self,
               sim_state: SimulationState,
               instructions: Tuple[Instruction, ...],
               reports: Tuple[str, ...]):
        self._report_entities(logger=self.vehicle_logger,
                              entities=sim_state.vehicles.values(),
                              sim_time=sim_state.sim_time)
        self._report_entities(logger=self.request_logger,
                              entities=sim_state.requests.values(),
                              sim_time=sim_state.sim_time)
        self._report_entities(logger=self.instruction_logger,
                              entities=instructions,
                              sim_time=sim_state.sim_time)
        for report in reports:
            self.run_logger.info(report)
