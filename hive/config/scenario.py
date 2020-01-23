from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder


class Scenario(NamedTuple):
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
            currency_name=d['currency_name'],
            currency_symbol=d['currency_symbol']
        )
