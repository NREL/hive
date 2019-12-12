from typing import NamedTuple, TypedDict, Dict

from hive.util.typealiases import SimTime


class Config(TypedDict):
    io: Dict
    sim: Dict
    network: Dict

# class IO(NamedTuple, Config):
#     working_directory: str = "/tmp"
#
#
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
