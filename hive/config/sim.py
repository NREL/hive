from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple

from hive.config.config_builder import ConfigBuilder
from hive.model.vehicle.schedules.schedule_type import ScheduleType
from hive.model.sim_time import SimTime
from hive.util.units import Seconds


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: Seconds
    start_time: SimTime
    end_time: SimTime
    sim_h3_resolution: int
    sim_h3_search_resolution: int
    request_cancel_time_seconds: int
    schedule_type: ScheduleType

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'sim_name',
            'start_time',
            'end_time',
        )

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
        start_time = SimTime.build(d['start_time'])
        if isinstance(start_time, IOError):
            return start_time

        end_time = SimTime.build(d['end_time'])
        if isinstance(end_time, IOError):
            return end_time

        schedule_type = ScheduleType.from_string(d['schedule_type'])

        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=int(d['timestep_duration_seconds']),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
            request_cancel_time_seconds=int(d['request_cancel_time_seconds']),
            schedule_type=schedule_type
        )

    def asdict(self) -> Dict:
        return self._asdict()
