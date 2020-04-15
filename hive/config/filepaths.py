from __future__ import annotations

import hashlib
import os
import logging
from typing import NamedTuple, Tuple, Dict, Optional

from pkg_resources import resource_filename

from hive.config import ConfigBuilder

log = logging.getLogger(__name__)


class FilePaths(NamedTuple):
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    vehicle_types_file: str
    road_network_file: Optional[str]
    geofence_file: Optional[str]
    rate_structure_file: Optional[str]
    charging_price_file: Optional[str]
    demand_forecast_file: Optional[str]

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'road_network_file': None,
            'geofence_file': None,
            'rate_structure_file': None,
            'charging_price_file': None,
            'demand_forecast_file': None,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'vehicles_file',
            'requests_file',
            'bases_file',
            'stations_file',
            'vehicle_types_file'
        )

    @classmethod
    def build(cls, config: Dict, cache: Optional[Dict]) -> FilePaths:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: FilePaths.from_dict(c, cache),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict, cache: Optional[Dict]) -> FilePaths:
        d['vehicles_file'] = resource_filename("hive.resources.vehicles", d['vehicles_file'])
        d['bases_file'] = resource_filename("hive.resources.bases", d['bases_file'])
        d['stations_file'] = resource_filename("hive.resources.stations", d['stations_file'])
        d['requests_file'] = resource_filename("hive.resources.requests", d['requests_file'])
        d['vehicle_types_file'] = resource_filename("hive.resources.vehicle_types", d['vehicle_types_file'])

        if d['road_network_file']:
            d['road_network_file'] = resource_filename("hive.resources.road_network", d['road_network_file'])
        if d['geofence_file']:
            d['geofence_file'] = resource_filename("hive.resources.geofence", d['geofence_file'])
        if d['rate_structure_file']:
            d['rate_structure_file'] = resource_filename("hive.resources.service_prices", d['rate_structure_file'])
        if d['charging_price_file']:
            d['charging_price_file'] = resource_filename("hive.resources.charging_prices", d['charging_price_file'])
        if d['demand_forecast_file']:
            d['demand_forecast_file'] = resource_filename("hive.resources.demand_forecast", d['demand_forecast_file'])

        file_paths_config = FilePaths(**d)

        if cache:
            for name, path in file_paths_config.asdict(absolute_paths=True).items():
                if path:
                    cls._check_md5_checksum(path, cache[name])

        return file_paths_config

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
