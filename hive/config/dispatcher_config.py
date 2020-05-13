from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple, Optional

from hive.config.config_builder import ConfigBuilder
from hive.util.units import Ratio, Seconds, Kilometers


class DispatcherConfig(NamedTuple):
    default_update_interval_seconds: Seconds
    matching_range_km_threshold: Kilometers
    charging_range_km_threshold: Kilometers
    base_charging_range_km_threshold: Kilometers
    ideal_fastcharge_soc_limit: Ratio
    max_search_radius_km: Kilometers

    valid_dispatch_states: Tuple[str, ...]
    active_states: Tuple[str, ...]

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'default_update_interval_seconds': 60 * 15,
            'matching_range_km_threshold': 20,
            'charging_range_km_threshold': 20,
            'base_charging_range_km_threshold': 100,
            'ideal_fastcharge_soc_limit': 0.8,
            'max_search_radius_km': 100.0,
            'valid_dispatch_states': ('idle', 'repositioning'),
            'active_states': (
                'idle',
                'repositioning',
                'dispatchtrip',
                'servicingtrip',
                'dispatchstation',
                'chargingstation',
            )
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
        try:
            d['valid_dispatch_states'] = tuple(d['valid_dispatch_states'])
            d['active_states'] = tuple(d['active_states'])
        except ValueError:
            return IOError("valid_dispatch_states and active_states must be in a list format")

        return DispatcherConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()
