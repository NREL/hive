from __future__ import annotations

from typing import NamedTuple, Dict
from datetime import datetime

from hive.config import ConfigBuilder
from hive.util.typealiases import SimTime
from hive.util.units import Seconds


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
    def build(cls, config: Dict = None) -> Sim:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Sim:
        try:
            start_time = int(datetime.fromisoformat(d['start_time']).timestamp())
            end_time = int(datetime.fromisoformat(d['end_time']).timestamp())
        except TypeError:
            try:
                start_time = int(d['start_time'])
                end_time = int(d['end_time'])
            except ValueError:
                raise IOError(
                    "Unable to parse datetime. \
                    Make sure the time is either a unix time integer or an ISO 8601 string")

        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=int(d['timestep_duration_seconds']),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
        )
