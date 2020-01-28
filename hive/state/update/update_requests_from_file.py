from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.state.update.update_requests import update_requests_from_iterator
from hive.util.dict_reader_stepper import DictReaderStepper


class UpdateRequestsFromFile(NamedTuple, SimulationUpdateFunction):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """
    reader: DictReaderStepper

    @classmethod
    def build(cls, request_file: str):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdateFunction

        :param request_file: file path for requests
        :return: a SimulationUpdate function pointing at the first line of a request file
        """
        req_path = Path(request_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")
        else:
            stepper = DictReaderStepper.from_file(request_file, "departure_time")
            return UpdateRequestsFromFile(stepper)

    def update(self,
               sim_state: SimulationState,
               env: Environment) -> Tuple[SimulationUpdateResult, Optional[UpdateRequestsFromFile]]:
        """
        add requests from file when the simulation reaches the request's time

        :param sim_state: the current sim state
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.current_time
        result = update_requests_from_iterator(self.reader.read_until_value(current_sim_time), sim_state)

        return result, None

