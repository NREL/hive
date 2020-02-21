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
    road_network_file: Optional[str]
    geofence_file: Optional[str]
    rate_structure_file: Optional[str]
    charging_price_file: Optional[str]

    # Log files
    run_log_file: Optional[str]
    sim_log_file: Optional[str]
    error_log_file: Optional[str]

    log_vehicles: bool
    log_requests: bool
    log_stations: bool
    log_dispatcher: bool
    log_manager: bool

    log_time_step: Seconds

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'working_directory': "",

            'road_network_file': None,
            'geofence_file': None,
            'rate_structure_file': None,
            'charging_price_file': None,

            'run_log_file': 'run.log',
            'sim_log_file': 'sim.log',
            'error_log_file': 'error.log',

            'log_vehicles': False,
            'log_requests': False,
            'log_stations': False,
            'log_dispatcher': False,
            'log_manager': False,

            'log_time_step': 1,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'vehicles_file',
            'requests_file',
            'bases_file',
            'stations_file',
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
        return IO(
            working_directory=d['working_directory'],

            vehicles_file=d['vehicles_file'],
            requests_file=d['requests_file'],
            rate_structure_file=d['rate_structure_file'],
            charging_price_file=d['charging_price_file'],
            bases_file=d['bases_file'],
            stations_file=d['stations_file'],
            road_network_file=d['road_network_file'],
            geofence_file=d['geofence_file'],

            run_log_file=d['run_log_file'],
            sim_log_file=d['sim_log_file'],
            error_log_file=d['error_log_file'],

            log_vehicles=d['log_vehicles'],
            log_requests=d['log_requests'],
            log_stations=d['log_stations'],
            log_dispatcher=d['log_dispatcher'],
            log_manager=d['log_manager'],

            log_time_step=d['log_time_step'],

        )
