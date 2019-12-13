from __future__ import annotations

from typing import Tuple

import json
import logging

from hive.state.simulation_state import SimulationState
from hive.dispatcher.instruction import Instruction
from hive.reporting.reporter import Reporter
from hive.config import IO


class DetailedReporter(Reporter):
    """
    A class that generates very detailed reports for the simulation.
    """

    def __init__(self, io: IO):
        self.run_logger = logging.getLogger(io.run_log)
        self.vehicle_logger = logging.getLogger(io.vehicle_log)
        self.request_logger = logging.getLogger(io.request_log)
        self.instruction_logger = logging.getLogger(io.instruction_log)

    def _report_entities(self, logger, entities, sim_time):
        for e in entities:
            log_dict = e._asdict()
            log_dict['sim_time'] = sim_time
            entry = json.dumps(log_dict, default=str)
            logger.info(entry)

    def report(self, sim_state: SimulationState, instructions: Tuple[Instruction, ...]):
        """
        Takes in a simulation state and a tuple of instructions and writes the appropriate information.
        :param sim_state:
        :param instructions:
        :return:
        """
        self._report_entities(logger=self.vehicle_logger,
                              entities=sim_state.vehicles.values(),
                              sim_time=sim_state.sim_time)
        self._report_entities(logger=self.request_logger,
                              entities=sim_state.requests.values(),
                              sim_time=sim_state.sim_time)
        self._report_entities(logger=self.instruction_logger,
                              entities=instructions,
                              sim_time=sim_state.sim_time)
