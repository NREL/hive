from __future__ import annotations

from typing import NamedTuple, Dict, Union
from datetime import datetime

from hive.config import ConfigBuilder
from hive.util.typealiases import SimTime
from hive.util.units import Seconds


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: Seconds
    start_time: SimTime
    end_time: SimTime
    date_format: str
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
        date_format = d['date_format']
        if date_format:
            try:
                start_dt = datetime.strptime(d['start_time'], date_format)
                end_dt = datetime.strptime(d['end_time'], date_format)
            except ValueError:
                raise IOError("Unable to parse datetime. Make sure the format matches config.sim.date_format")
            start_time = int(start_dt.timestamp())
            end_time = int(end_dt.timestamp())
        else:
            try:
                start_time = int(d['start_time'])
                end_time = int(d['end_time'])
            except ValueError:
                raise IOError("Unable to parse datetime. Make sure the format matches config.sim.date_format")

        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=int(d['timestep_duration_seconds']),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
            date_format=date_format,
        )
