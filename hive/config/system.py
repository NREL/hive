from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Optional

from hive.config.config_builder import ConfigBuilder


class System(NamedTuple):
    local_parallelism: int
    local_parallelism_timeout_sec: int

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'local_parallelism': 1,
            'local_parallelism_timeout_sec': 60
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (

        )

    @classmethod
    def build(cls, config: Optional[Dict] = None) -> System:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: System.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> System:
        return System(**d)

    def asdict(self) -> Dict:
        return self._asdict()
