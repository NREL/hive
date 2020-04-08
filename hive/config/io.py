from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Optional

from hive.config import ConfigBuilder
from hive.util.units import Seconds


class IO(NamedTuple):
    working_directory: str

    # Input files
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

    log_vehicles: bool
    log_requests: bool
    log_stations: bool
    log_dispatcher: bool
    log_manager: bool

    log_period_seconds: Seconds
    progress_period_seconds: Seconds

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'working_directory': "",

            'road_network_file': None,
            'geofence_file': None,
            'rate_structure_file': None,
            'charging_price_file': None,
            'demand_forecast_file': None,

            'log_vehicles': False,
            'log_requests': False,
            'log_stations': False,
            'log_dispatcher': False,
            'log_manager': False,

            'log_period_seconds': 60,
            'progress_period_seconds': 3600,
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
    def build(cls, config: Dict = None) -> IO:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: IO.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> IO:
        return IO(**d)

