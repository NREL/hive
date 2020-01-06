from __future__ import annotations

import logging
import os

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder


def _setup_logger(name, log_file, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    fh = logging.FileHandler(log_file)
    logger.addHandler(fh)

    return logger


class IO(NamedTuple):
    output_directory: str
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    run_log: str
    vehicle_log: str
    request_log: str
    instruction_log: str

    @classmethod
    def default_config(cls) -> Dict:
        return {'output_directory': ""}

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
        # TODO: Move logging outside of the config construction.
        output_dir = d['output_directory']
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        run_logger = _setup_logger(name='run_log',
                                   log_file=os.path.join(output_dir, 'run.log'), )
        vehicle_logger = _setup_logger(name='vehicle_log',
                                       log_file=os.path.join(output_dir, 'vehicle.log'))
        request_logger = _setup_logger(name='request_log',
                                       log_file=os.path.join(output_dir, 'request.log'))
        instruction_logger = _setup_logger(name='instruction_log',
                                           log_file=os.path.join(output_dir, 'instruction.log'))

        return IO(
            output_directory=d['output_directory'],
            vehicles_file=d['vehicles_file'],
            requests_file=d['requests_file'],
            bases_file=d['bases_file'],
            stations_file=d['stations_file'],
            run_log=run_logger.name,
            vehicle_log=vehicle_logger.name,
            request_log=request_logger.name,
            instruction_log=instruction_logger.name,
        )
