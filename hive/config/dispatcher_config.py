from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple, Optional

from hive.config import ConfigBuilder
from hive.util.units import Ratio, Seconds, Kilometers


class DispatcherConfig(NamedTuple):
    default_update_interval_seconds: Seconds
    matching_low_soc_threshold: Ratio
    charging_low_soc_threshold: Ratio
    ideal_fastcharge_soc_limit: Ratio
    max_search_radius_km: Kilometers
    base_vehicles_charging_limit: Optional[int]

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'default_update_interval_seconds': 60 * 15,
            'matching_low_soc_threshold': 0.2,
            'charging_low_soc_threshold': 0.2,
            'ideal_fastcharge_soc_limit': 0.8,
            'base_vehicles_charging_limit': None,
            'max_search_radius_km': 100.0,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def build(cls, config: Optional[Dict] = None) -> DispatcherConfig:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: DispatcherConfig.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[IOError, DispatcherConfig]:
        return DispatcherConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()
