from __future__ import annotations

from typing import Tuple

import json

from hive.simulationstate.simulation_state import SimulationState
from hive.dispatcher.instruction import Instruction
from hive.reporting.reporter import Reporter


class DetailedReporter(Reporter):
    """
    A class that generates very detailed reports for the simulation.
    """

    def __init__(self, config):
        # TODO: replace once config is implemented.
        self.vehicle_log = config.vehicle_log
        self.request_log = config.request_log
        self.instruction_log = config.instruction_log

    def _report_entities(self, log, entities, sim_time):
        for e in entities:
            log_dict = dict(e)
            log_dict['sim_time'] = sim_time
            entry = json.dumps(log_dict)
            log.info(entry)

    def report(self, sim_state: SimulationState, instructions: Tuple[Instruction, ...]):
        """
        Takes in a simulation state and a tuple of instructions and writes the appropriate information.
        :param sim_state:
        :param instructions:
        :return:
        """
        self._report_entities(log=self.vehicle_log, entities=sim_state.vehicles.values(), sim_time=sim_state.sim_time)
        self._report_entities(log=self.request_log, entities=sim_state.requests.values(), sim_time=sim_state.sim_time)
        self._report_entities(log=self.instruction_log, entities=instructions, sim_time=sim_state.sim_time)
