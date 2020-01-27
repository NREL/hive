from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder


class Scenario(NamedTuple):
    scenario_directory: str
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    currency_name: str
    currency_symbol: str

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'currency_name': "Dollars",  # formal name of currency used
            'currency_symbol': "$",
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {}

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, Scenario]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Scenario.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Scenario:
        return Scenario(
            scenario_directory=d['scenario_directory'],
            vehicles_file=d['vehicles_file'],
            requests_file=d['requests_file'],
            bases_file=d['bases_file'],
            stations_file=d['stations_file'],
            currency_name=d['currency_name'],
            currency_symbol=d['currency_symbol']
        )
