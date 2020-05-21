from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Optional, Set

from hive.config.config_builder import ConfigBuilder
from hive.config.filepaths import FilePaths
from hive.util.units import Seconds


class IO(NamedTuple):
    input_directory: str
    output_directory: str

    # Input files
    file_paths: FilePaths

    log_run: bool
    log_sim: bool
    log_sim_config: Set[Optional[str]]

    log_period_seconds: Seconds

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'output_directory': "",

            'log_run': True,
            'log_sim': True,
            'log_sim_config': {
                'vehicle_report',
                'request_report',
                'add_request',
                'cancel_request',
                'station_report',
                'charge_event',
                'dispatcher',
            },

            'log_period_seconds': 60,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'file_paths',
        )

    @classmethod
    def build(cls, config: Dict = None, cache: Optional[Dict] = None) -> IO:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: IO.from_dict(c, cache),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict, cache: Optional[Dict]) -> IO:
        d['file_paths'] = FilePaths.build(d['file_paths'], cache)
        d['log_sim_config'] = set(d['log_sim_config'])

        return IO(**d)

    def asdict(self) -> Dict:
        file_paths_dict = self.file_paths.asdict()
        self_dict = self._asdict()
        self_dict['file_paths'] = file_paths_dict

        return self_dict

    @property
    def write_outputs(self):
        return self.log_run or self.log_sim
