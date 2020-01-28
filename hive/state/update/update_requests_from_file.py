from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Optional
from datetime import datetime

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
    def build(cls, request_file: str, env: Environment):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdateFunction

        :param request_file: file path for requests
        :return: a SimulationUpdate function pointing at the first line of a request file
        """

        if env.config.sim.date_format:
            def stop_condition(value: str) -> bool:
                dt = datetime.strptime(value, env.config.sim.date_format)
                return dt.timestamp() < 0
        else:
            def stop_condition(value: str) -> bool:
                return int(value) < 0

        req_path = Path(request_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")
        else:
            stepper = DictReaderStepper.from_file(request_file, "departure_time", stop_condition)
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

        if env.config.sim.date_format:
            def stop_condition(value: str) -> bool:
                dt = datetime.strptime(value, env.config.sim.date_format)
                return dt.timestamp() < current_sim_time
        else:
            def stop_condition(value: str) -> bool:
                return int(value) < current_sim_time

        result = update_requests_from_iterator(
            self.reader.read_until_stop_condition(stop_condition),
            sim_state,
            env
        )

        return result, None
