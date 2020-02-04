from __future__ import annotations

from typing import NamedTuple, Dict, Optional

from hive.config import ConfigBuilder


class IO(NamedTuple):
    working_directory: str
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    geofence_file: str
    rate_structure_file: Optional[str]
    charging_price_file: Optional[str]

    run_log: Optional[str]
    vehicle_log: Optional[str]
    request_log: Optional[str]

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'working_directory': "",
            'run_log': None,
            'vehicle_log': None,
            'request_log': None,
            'rate_structure_file': None,
            'charging_price_file': None
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {
            'vehicles_file': str,
            'requests_file': str,
            'bases_file': str,
            'stations_file': str,
            'geofence_file': str,
        }

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
        return IO(
            working_directory=d['working_directory'],
            vehicles_file=d['vehicles_file'],
            requests_file=d['requests_file'],
            rate_structure_file=d['rate_structure_file'],
            charging_price_file=d['charging_price_file'],
            bases_file=d['bases_file'],
            stations_file=d['stations_file'],
            geofence_file=d['geofence_file'],
            run_log=d['run_log'],
            vehicle_log=d['vehicle_log'],
            request_log=d['request_log'],
        )
