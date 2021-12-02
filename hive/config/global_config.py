from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Dict, Set

from hive.config.config_builder import ConfigBuilder
from hive.reporting.reporter import ReportType


class GlobalConfig(NamedTuple):
    global_settings_file_path: str
    output_base_directory: str
    local_parallelism: int
    local_parallelism_timeout_sec: int
    log_run: bool
    log_events: bool
    log_states: bool
    log_instructions: bool
    log_stats: bool
    log_level: str
    log_sim_config: Set[ReportType]
    log_station_capacities: bool
    log_time_step_stats: bool
    log_fleet_time_step_stats: bool
    lazy_file_reading: bool
    wkt_x_y_ordering: bool


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
            'log_states',
            'log_events',
            'log_instructions',
            'log_stats',
            'log_level',
            'log_sim_config',
            'log_time_step_stats',
            'log_fleet_time_step_stats',
            'lazy_file_reading',
            'wkt_x_y_ordering',
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
        output_base_directory_absolute = Path(d['output_base_directory']).expanduser() if d[
            'output_base_directory'].startswith("~") else Path(
            d['output_base_directory'])
        d['output_base_directory'] = str(output_base_directory_absolute)

        # convert list of logged report types to a Set
        d['log_sim_config'] = set(ReportType.from_string(rt) for rt in d['log_sim_config']) if d[
            'log_sim_config'] else set()

        # store the .hive.yaml file path used
        d['global_settings_file_path'] = global_settings_file_path
        return GlobalConfig(**d)

    def asdict(self) -> Dict:
        return self._asdict()
    
    @property
    def write_outputs(self):
        return self.log_run or self.log_states or self.log_events or self.log_stats or self.log_station_capacities or \
               self.log_instructions or self.log_time_step_stats or self.log_fleet_time_step_stats
