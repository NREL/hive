from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple, Optional
from pkg_resources import resource_filename

from hive.config import ConfigBuilder
from hive.util import Kilometers


class Network(NamedTuple):
    network_type: str
    default_speed_kmph: float
    max_search_radius_km: Kilometers

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'network_type': "euclidean",
            'default_speed_kmph': 40.0,
            'max_search_radius_km': 100.0,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, Network]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Network.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Network:


        return Network(**d)
