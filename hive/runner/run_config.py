from typing import NamedTuple, TypedDict, Dict

from hive.util.typealiases import SimTime


class Config(TypedDict):
    io: Dict
    sim: Dict
    network: Dict

# class IO(NamedTuple):
#     working_directory: str = "/tmp"
#
#
# class Sim(NamedTuple):
#     timestep_duration_seconds: SimTime = 1
#     start_time_seconds: SimTime = 0
#     end_time_seconds: SimTime = 86400
#
#
# class Network(NamedTuple):
#     network_type: str = "euclidean"
#
#
# class RunConfig(NamedTuple):
#     sim: Sim
#     io: IO
#     network: Network
