from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder
from hive.util.typealiases import SimTime


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: SimTime
    start_time: SimTime
    end_time: SimTime
    sim_h3_resolution: int
    sim_h3_search_resolution: int

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'timestep_duration_seconds': 1,  # number of seconds per time step in Hive
            'start_time': 0,  # 12:00:00am today (range-inclusive value)
            'end_time': 86400,  # 12:00:00am next day (range-exclusive value)
            'sim_h3_resolution': 15,
            'sim_h3_search_resolution': 7,
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {'sim_name': str}

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, Sim]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Sim:
        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=d['timestep_duration_seconds'],
            start_time=d['start_time'],
            end_time=d['end_time'],
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
        )
