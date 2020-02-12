from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder
from hive.util.typealiases import SimTime
from hive.util.units import Seconds
from hive.util.parsers import time_parser


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: Seconds
    start_time: SimTime
    end_time: SimTime
    sim_h3_resolution: int
    sim_h3_search_resolution: int

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'timestep_duration_seconds': 1,  # number of seconds per time step in Hive
            'sim_h3_resolution': 15,
            'sim_h3_search_resolution': 7,
            'date_format': None,
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {
            'sim_name': str,
            'start_time': (str, int),
            'end_time': (str, int),
        }

    @classmethod
    def build(cls, config: Dict = None) -> Union[IOError, Sim]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[IOError, Sim]:
        start_time = time_parser(d['start_time'])
        if isinstance(start_time, IOError):
            return start_time

        end_time = time_parser(d['end_time'])
        if isinstance(end_time, IOError):
            return end_time

        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=int(d['timestep_duration_seconds']),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
        )