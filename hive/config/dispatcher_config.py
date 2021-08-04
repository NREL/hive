from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple, Optional

from hive.config.config_builder import ConfigBuilder
from hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from hive.util.units import Ratio, Seconds, Kilometers


class DispatcherConfig(NamedTuple):
    default_update_interval_seconds: Seconds
    matching_range_km_threshold: Kilometers
    charging_range_km_threshold: Kilometers
    charging_range_km_soft_threshold: Kilometers
    base_charging_range_km_threshold: Kilometers
    ideal_fastcharge_soc_limit: Ratio
    max_search_radius_km: Kilometers
    charging_search_type: ChargingSearchType

    idle_time_out_seconds: Seconds

    valid_dispatch_states: Tuple[str, ...]

    @classmethod
    def default_config(cls) -> Dict:
        return {}

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
            d['valid_dispatch_states'] = tuple(s.lower() for s in d['valid_dispatch_states'])
            d['charging_search_type'] = ChargingSearchType.from_string(d['charging_search_type'])
        except ValueError:
            return IOError("valid_dispatch_states and active_states must be in a list format")

        return DispatcherConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()
