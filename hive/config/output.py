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


class Output(NamedTuple):
    output_directory: str
    run_log: str
    vehicle_log: str
    request_log: str

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'output_directory': "",
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
    def build(cls, config: Dict = None) -> Union[Exception, Output]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Output.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Output:
        return Output(
            output_directory=d['output_directory'],
            run_log=d['run_log'],
            vehicle_log=d['vehicle_log'],
            request_log=d['request_log'],
        )
