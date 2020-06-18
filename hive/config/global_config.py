from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Dict, Optional, Set

from hive.config.config_builder import ConfigBuilder
from hive.util.units import Seconds


class GlobalConfig(NamedTuple):
    global_settings_file_path: str
    output_base_directory: str
    local_parallelism: int
    local_parallelism_timeout_sec: int
    log_run: bool
    log_sim: bool
    log_level: str
    log_sim_config: Set[Optional[str]]
    log_period_seconds: Seconds
    lazy_file_reading: bool
    track_stats: bool

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'output_base_directory',
            'local_parallelism',
            'local_parallelism_timeout_sec',
            'log_run',
            'log_sim',
            'log_level',
            'log_sim_config',
            'log_period_seconds',
            'lazy_file_reading',
            'track_stats',
        )

    @classmethod
    def build(cls, config: Dict, global_settings_file_path: str) -> GlobalConfig:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: GlobalConfig.from_dict(c, global_settings_file_path),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict, global_settings_file_path) -> GlobalConfig:
        # allow Posix-style home directory paths ('~')
        output_base_directory_absolute = Path(d['output_base_directory']).expanduser() if d['output_base_directory'].startswith("~") else Path(
            d['output_base_directory'])
        d['output_base_directory'] = str(output_base_directory_absolute)

        # convert list of logged report types to a Set
        d['log_sim_config'] = set(d['log_sim_config'])

        # store the .hive.yaml file path used
        d['global_settings_file_path'] = global_settings_file_path
        return GlobalConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()

    @property
    def write_outputs(self):
        return self.log_run or self.log_sim
