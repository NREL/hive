from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Optional, Set

from hive.config.config_builder import ConfigBuilder
from hive.util.units import Seconds


class GlobalConfig(NamedTuple):
    output_base_directory: str
    log_run: bool
    log_sim: bool
    log_sim_config: Set[Optional[str]]
    log_period_seconds: Seconds

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'output_base_directory',
            'log_run',
            'log_sim',
            'log_sim_config',
            'log_period_seconds'
        )

    @classmethod
    def build(cls, config: Dict = None) -> GlobalConfig:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: GlobalConfig.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> GlobalConfig:
        d['log_sim_config'] = set(d['log_sim_config'])
        return GlobalConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()

    @property
    def write_outputs(self):
        return self.log_run or self.log_sim
