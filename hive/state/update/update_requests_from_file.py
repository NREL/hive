from __future__ import annotations

import _csv
import _io
import csv
import functools as ft
from pathlib import Path
from typing import Dict, TextIO

from hive.model.request import Request
from hive.state.simulation_state import SimulationState, RequestId
from hive.state.update.simulation_update import SimulationUpdate
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.state.update.update_requests import update_requests_from_iterator
from hive.util.typealiases import SimTime


class UpdateRequestsFromFile(SimulationUpdate):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """

    def __init__(self, request_file: str):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdate function

        :param request_file: file path for requests
        :return: a SimulationUpdate function pointing at the first line of a request file
        """
        req_path = Path(request_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")
        else:
            self.file = open(req_path, newline='')
            self.requests = csv.DictReader(self.file)

    def update(self, initial_sim_state: SimulationState) -> SimulationUpdateResult:
        """
        add requests from file when the simulation reaches the request's time

        :param initial_sim_state: the current sim state
        :return: sim state plus new requests
        """
        it = RequestFileIterator(self.requests, self.file, initial_sim_state.sim_time)

        return update_requests_from_iterator(it, initial_sim_state)


class RequestFileIterator:
    def __init__(self, reader: _csv.reader, file: TextIO, sim_time: SimTime):
        """
        creates an iterator up to a departure time boundary, inclusive

        :param reader: file reader
        :param file: source file handler
        :param sim_time: time we are scheduling up to and including
        """
        self.reader = reader
        self.file = file
        self.sim_time = sim_time

    def __next__(self) -> Dict[str, str]:
        """
        attempts to grab the next row from the file

        :return: a row, or, raises a StopIteration when end-of-file
        :raises StopIteration: when file is empty, or, if all departures up to the present sim time have been found
        """
        pos_before_iter = self.file.tell()
        row = next(self.reader)
        row_time = int(row['departure_time'])
        if row_time > self.sim_time:
            self.file.seek(pos_before_iter)
            raise StopIteration
        else:
            return row

    def __iter__(self):
        return self
