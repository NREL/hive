from __future__ import annotations

from typing import NamedTuple, Dict, Optional, Tuple

from nrel.hive.config.config_builder import ConfigBuilder
from nrel.hive.model.sim_time import SimTime
from nrel.hive.model.vehicle.schedules.schedule_type import ScheduleType
from nrel.hive.util.units import Seconds
from nrel.hive.util import Ratio


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: Seconds
    start_time: SimTime
    end_time: SimTime
    sim_h3_resolution: int
    sim_h3_search_resolution: int
    request_cancel_time_seconds: int
    schedule_type: ScheduleType
    min_delta_energy_change: Ratio = 0.0001
    seed: Optional[int] = 0

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            "sim_name",
            "start_time",
            "end_time",
        )

    @classmethod
    def build(cls, config: Optional[Dict] = None) -> Sim:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config,
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Sim:
        start_time = SimTime.build(d["start_time"])

        end_time = SimTime.build(d["end_time"])

        schedule_type = ScheduleType.from_string(d["schedule_type"])

        sim_h3_resolution = int(d["sim_h3_resolution"])
        sim_h3_search_resolution = int(d["sim_h3_search_resolution"])

        if sim_h3_search_resolution >= sim_h3_resolution:
            raise ValueError("sim_h3_search_resolution must be less than sim_h3_resolution")

        return Sim(
            sim_name=d["sim_name"],
            timestep_duration_seconds=int(d["timestep_duration_seconds"]),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=sim_h3_resolution,
            sim_h3_search_resolution=sim_h3_search_resolution,
            request_cancel_time_seconds=int(d["request_cancel_time_seconds"]),
            schedule_type=schedule_type,
        )

    def asdict(self) -> Dict:
        return self._asdict()
