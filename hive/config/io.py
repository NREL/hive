from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Optional

from hive.config import ConfigBuilder
from hive.config.filepaths import FilePaths
from hive.util.units import Seconds


class IO(NamedTuple):
    working_directory: str

    # Input files
    file_paths: FilePaths

    log_vehicles: bool
    log_requests: bool
    log_stations: bool
    log_dispatcher: bool
    log_manager: bool

    log_period_seconds: Seconds
    progress_period_seconds: Seconds

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'working_directory': "",

            'log_vehicles': False,
            'log_requests': False,
            'log_stations': False,
            'log_dispatcher': False,
            'log_manager': False,

            'log_period_seconds': 60,
            'progress_period_seconds': 3600,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'file_paths',
        )

    @classmethod
    def build(cls, config: Dict = None) -> IO:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: IO.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> IO:
        d['file_paths'] = FilePaths.build(d['file_paths'])

        return IO(**d)

    def asdict(self) -> Dict:
        file_paths_dict = self.file_paths.asdict()
        self_dict = self._asdict()
        self_dict['file_paths'] = file_paths_dict

        return self_dict
