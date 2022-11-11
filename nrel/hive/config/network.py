from __future__ import annotations

from typing import NamedTuple, Dict, Optional, Tuple

from nrel.hive.config.config_builder import ConfigBuilder


class Network(NamedTuple):
    network_type: str
    default_speed_kmph: float

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def build(cls, config: Optional[Dict] = None) -> Network:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Network.from_dict(c),
            config=config,
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Network:
        return Network(**d)

    def asdict(self) -> Dict:
        return self._asdict()
