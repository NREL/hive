from __future__ import annotations

import hashlib
import logging
import os
from typing import NamedTuple, Tuple, Dict, Optional, Set

from hive.config.config_builder import ConfigBuilder
from hive.util.units import Seconds

log = logging.getLogger(__name__)


class Input(NamedTuple):

    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    mechatronics_file: str
    road_network_file: Optional[str]
    geofence_file: Optional[str]
    rate_structure_file: Optional[str]
    charging_price_file: Optional[str]
    demand_forecast_file: Optional[str]

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'vehicles_file': 'vehicles.csv',
            'requests_file': 'requests.csv',
            'bases_file': 'bases.csv',
            'stations_file': 'stations.csv',
            'mechatronics_file': 'mechatronics.csv',
            'road_network_file': None,
            'geofence_file': None,
            'rate_structure_file': None,
            'charging_price_file': None,
            'demand_forecast_file': None,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def build(cls, config: Dict = None, cache: Optional[Dict] = None) -> Input:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Input.from_dict(c, cache),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict, cache: Optional[Dict]) -> Input:
        d['log_sim_config'] = set(d['log_sim_config'])

        input = Input(**d)

        if cache:
            for name, path in input.asdict(absolute_paths=True).items():
                if path:
                    cls._check_md5_checksum(path, cache[name])

        return Input(**d)

    @staticmethod
    def _check_md5_checksum(filepath: str, existing_md5_sum: str):
        with open(filepath, 'rb') as f:
            data = f.read()
            new_md5_sum = hashlib.md5(data).hexdigest()
            if new_md5_sum != existing_md5_sum:
                log.warning(f'this is a cached config file but the file {filepath} has changed since the last run')

    def asdict(self, absolute_paths=False) -> Dict:
        if absolute_paths:
            return self._asdict()
        else:
            out_dict = {}
            for k, v in self._asdict().items():
                if not v:
                    out_dict[k] = v
                else:
                    out_dict[k] = os.path.basename(v)

            return out_dict

