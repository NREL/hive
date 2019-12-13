from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder


class IO(NamedTuple):
    working_directory: str
    vehicles_file: str

    @classmethod
    def default_config(cls) -> Dict:
        return {'working_directory': "/tmp"}

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {'vehicles_file': str}

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
            vehicles_file=d['vehicles_file']
        )
