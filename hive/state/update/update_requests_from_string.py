from __future__ import annotations

from csv import DictReader
from typing import List, Dict, NamedTuple, Tuple, Optional

from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.state.update.update_requests import update_requests_from_iterator
from hive.util.typealiases import SimTime


class UpdateRequestsFromString(NamedTuple, SimulationUpdateFunction):
    """
    loads requests from a newline-delimited string in csv format
    """
    header: str
    requests: List[str]
    num_rows: int
    row_position: int = 0

    @classmethod
    def build(cls, string_requests: str):

        src = string_requests.split()

        return UpdateRequestsFromString(
            header=src[0],
            requests=src[1:],
            num_rows=len(src) - 1
        )

    def update(self,
               simulation_state: SimulationState) -> Tuple[SimulationUpdateResult, Optional[UpdateRequestsFromString]]:
        """
        add requests from file when the simulation reaches the request's time

        :param simulation_state: the current sim state
        :return: sim state plus new requests
        """
        subset = [self.header, ] + self.requests[self.row_position:]
        reader = DictReader(subset)
        it = RequestStringIterator(reader, simulation_state.current_time, self.row_position)
        sim_updated = update_requests_from_iterator(it, simulation_state)

        next_update = self._replace(row_position=it.row_position)

        return sim_updated, next_update


class RequestStringIterator:
    def __init__(self, requests: DictReader, sim_time: SimTime, row_position: int):
        self.requests = requests
        self.sim_time = sim_time
        self.row_position = row_position

    def __iter__(self):
        return self

    def __next__(self) -> Dict[str, str]:
        """
        attempts to grab the next row from the string

        :return: a row, or, raises a StopIteration when end-of-file
        :raises StopIteration: when source is empty, or, if all departures up to the present sim time have been found
        """
        row = next(self.requests)
        row_time = int(row['departure_time'])
        if row_time > self.sim_time:
            raise StopIteration
        else:
            self.row_position = self.row_position + 1
            return row
