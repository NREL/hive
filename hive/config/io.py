from __future__ import annotations

import logging

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder


def _setup_logger(name, log_file, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    fh = logging.FileHandler(log_file)
    logger.addHandler(fh)

    return logger


class IO(NamedTuple):
    working_directory: str
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    run_log: str
    vehicle_log: str
    request_log: str

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'working_directory': "",
            'run_log': None,
            'vehicle_log': None,
            'request_log': None,
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {
            'vehicles_file': str,
            'requests_file': str,
            'bases_file': str,
            'stations_file': str,
        }

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, IO]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: IO.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> IO:
        return IO(
            working_directory=d['working_directory'],
            vehicles_file=d['vehicles_file'],
            requests_file=d['requests_file'],
            bases_file=d['bases_file'],
            stations_file=d['stations_file'],
            run_log=d['run_log'],
            vehicle_log=d['vehicle_log'],
            request_log=d['request_log'],
        )
