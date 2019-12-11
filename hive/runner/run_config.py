from typing import NamedTuple

from hive.util.typealiases import Time


class IO(NamedTuple):
    working_directory: str
    request_file: str
    vehicles_file: str
    stations_file: str
    bases_file: str


class Sim(NamedTuple):
    timestep_duration_seconds: Time = 1
    start_time_seconds: Time = 0
    end_time_seconds: Time = 86400


class Network(NamedTuple):
    network_type: str
    network_file: str


class RunConfig(NamedTuple):
    sim: Sim
    io: IO
