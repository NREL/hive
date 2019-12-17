from csv import DictReader
from typing import List, Dict

from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdate
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.state.update.update_requests import update_requests_from_iterator
from hive.util.typealiases import SimTime


class UpdateRequestsFromString(SimulationUpdate):
    """
    loads requests from a newline-delimited string in csv format
    """

    def __init__(self, string_requests: str):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdate function
        :param string_requests: requests as a string, with header
        :return: a SimulationUpdate function based on the string data
        """
        src = string_requests.split()
        self.header = src[0]
        self.requests = src[1:]
        self.num_rows = len(self.requests)
        self.row_position = 0

    def update(self, initial_sim_state: SimulationState) -> SimulationUpdateResult:
        """
        add requests from file when the simulation reaches the request's time
        :param initial_sim_state: the current sim state
        :return: sim state plus new requests
        """
        subset = [self.header,] + self.requests[self.row_position:]
        reader = DictReader(subset)
        it = RequestStringIterator(reader, initial_sim_state.sim_time, self.row_position)
        sim_updated = update_requests_from_iterator(it, initial_sim_state)
        self.row_position = it.row_position
        return sim_updated


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
