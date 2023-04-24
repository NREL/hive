from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import NamedTuple, Tuple, Dict, Optional

from nrel.hive.config.config_builder import ConfigBuilder
from nrel.hive.util import fs

log = logging.getLogger(__name__)


class Input(NamedTuple):
    scenario_directory: str  # loaded from command line
    scenario_file: str  # loaded from command line as well
    vehicles_file: str
    requests_file: str
    bases_file: str
    stations_file: str
    mechatronics_file: str
    chargers_file: str
    schedules_file: Optional[str] = None
    road_network_file: Optional[str] = None
    geofence_file: Optional[str] = None
    rate_structure_file: Optional[str] = None
    charging_price_file: Optional[str] = None
    fleets_file: Optional[str] = None

    @classmethod
    def default_config(cls) -> Dict:
        return {}

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return "vehicles_file", "requests_file", "stations_file", "bases_file"

    @classmethod
    def build(cls, config: Dict, scenario_file_path: Path, cache: Optional[Dict]) -> Input:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Input.from_dict(c, scenario_file_path, cache),
            config=config,
        )

    @classmethod
    def from_dict(cls, d: Dict, scenario_file_path: Path, cache: Optional[Dict]) -> Input:
        # add the (required) directories which should contain
        scenario_directory = scenario_file_path.parent
        scenario_file = scenario_file_path.name

        # required files
        vehicles_file = fs.construct_scenario_asset_path(
            d["vehicles_file"], scenario_directory, "vehicles"
        )
        requests_file = fs.construct_scenario_asset_path(
            d["requests_file"], scenario_directory, "requests"
        )
        stations_file = fs.construct_scenario_asset_path(
            d["stations_file"], scenario_directory, "stations"
        )
        bases_file = fs.construct_scenario_asset_path(d["bases_file"], scenario_directory, "bases")

        # may be found in hive.resources
        mechatronics_file = fs.construct_asset_path(
            d["mechatronics_file"],
            scenario_directory,
            "mechatronics",
            "mechatronics",
        )

        # optional files
        schedules_filename = (
            d["schedules_file"] if d.get("schedules_file") else "default_schedules.csv"
        )
        schedules_file = fs.construct_asset_path(
            schedules_filename, scenario_directory, "schedules", "schedules"
        )
        chargers_filename = d["chargers_file"] if d.get("chargers_file") else "default_chargers.csv"
        chargers_file = fs.construct_asset_path(
            chargers_filename, scenario_directory, "chargers", "chargers"
        )
        road_network_file = (
            fs.construct_scenario_asset_path(
                d["road_network_file"], scenario_directory, "road_network"
            )
            if d.get("road_network_file")
            else None
        )
        geofence_file = (
            fs.construct_scenario_asset_path(d["geofence_file"], scenario_directory, "geofence")
            if d.get("geofence_file")
            else None
        )
        rate_structure_file = (
            fs.construct_scenario_asset_path(
                d["rate_structure_file"], scenario_directory, "service_prices"
            )
            if d.get("rate_structure_file")
            else None
        )
        charging_price_file = (
            fs.construct_scenario_asset_path(
                d["charging_price_file"], scenario_directory, "charging_prices"
            )
            if d.get("charging_price_file")
            else None
        )
        fleets_file = (
            fs.construct_scenario_asset_path(d["fleets_file"], scenario_directory, "fleets")
            if d.get("fleets_file")
            else None
        )

        input_config = {
            "scenario_directory": str(scenario_directory),
            "scenario_file": scenario_file,
            "vehicles_file": vehicles_file,
            "requests_file": requests_file,
            "bases_file": bases_file,
            "stations_file": stations_file,
            "schedules_file": schedules_file,
            "chargers_file": chargers_file,
            "mechatronics_file": mechatronics_file,
            "road_network_file": road_network_file,
            "geofence_file": geofence_file,
            "rate_structure_file": rate_structure_file,
            "charging_price_file": charging_price_file,
            "fleets_file": fleets_file,
        }

        # if cache provided, check the file has a correct md5 hash value
        if cache:
            for (
                name,
                path,
            ) in input_config.items():  # input_config.asdict(absolute_paths=True).items():
                if path:
                    cls._check_md5_checksum(path, cache[name])

        return Input(
            scenario_directory=str(scenario_directory),
            scenario_file=scenario_file,
            vehicles_file=vehicles_file,
            requests_file=requests_file,
            bases_file=bases_file,
            stations_file=stations_file,
            schedules_file=schedules_file,
            chargers_file=chargers_file,
            mechatronics_file=mechatronics_file,
            road_network_file=road_network_file,
            geofence_file=geofence_file,
            rate_structure_file=rate_structure_file,
            charging_price_file=charging_price_file,
            fleets_file=fleets_file,
        )

    @staticmethod
    def _check_md5_checksum(filepath: str, existing_md5_sum: str):
        with open(filepath, "rb") as f:
            data = f.read()
            new_md5_sum = hashlib.md5(data).hexdigest()
            if new_md5_sum != existing_md5_sum:
                log.warning(
                    f"this is a cached config file but the file {filepath} has changed since the last run"
                )

    def asdict(self) -> Dict:
        return self._asdict()
