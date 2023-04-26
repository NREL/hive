from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Dict, Union, Optional

import pkg_resources
import yaml

from nrel.hive.config.config_builder import ConfigBuilder
from nrel.hive.config.dispatcher_config import DispatcherConfig
from nrel.hive.config.global_config import GlobalConfig
from nrel.hive.config.input import Input
from nrel.hive.config.network import Network
from nrel.hive.config.sim import Sim
from nrel.hive.util import fs

log = logging.getLogger(__name__)


class HiveConfig(NamedTuple):
    global_config: GlobalConfig
    input_config: Input
    sim: Sim
    network: Network
    dispatcher: DispatcherConfig

    scenario_output_directory: Path = Path("")

    @classmethod
    def build(
        cls,
        scenario_file_path: Path,
        config: Optional[Dict] = None,
        output_suffix: Optional[str] = None,
    ) -> Union[Exception, HiveConfig]:
        """
        builds a hive config by reading from a scenario file. optionally append additional key/value
        pairs and modify the datetime convention for naming output directories.
        :param scenario_file_path: path to the file to load as a HiveConfig
        :param config: optional overrides to the default config values (Default: None)
        :param output_suffix: directory name suffix to append to sim_name (by default, timestamp)
        :return: a hive config or an error
        """
        return ConfigBuilder.build(
            default_config={},
            required_config=(),
            config_constructor=lambda c: HiveConfig.from_dict(c, scenario_file_path, output_suffix),
            config=config,
        )

    @classmethod
    def from_dict(
        cls, d: Dict, scenario_file_path: Path, output_suffix: Optional[str]
    ) -> HiveConfig:
        # collect the global hive configuration
        global_config = fs.global_hive_config_search()

        root_logger = logging.getLogger("")
        root_logger.setLevel(global_config.log_level)

        if global_config.verbose:
            log.info(
                f"global hive configuration loaded from {global_config.global_settings_file_path}"
            )
            for k, v in global_config.asdict().items():
                log.info(f"  {k}: {v}")

        # start build using the Hive config defaults file
        defaults_file_str = pkg_resources.resource_filename(
            "nrel.hive.resources.defaults", "hive_config.yaml"
        )
        defaults_file = Path(defaults_file_str)

        with defaults_file.open("r") as f:
            conf = yaml.safe_load(f)

            # append input_config file to default configuration with overwrite
            conf["input"].update(d["input"])
            conf["sim"].update(d["sim"])
            conf["network"].update(d["network"])
            conf["dispatcher"].update(d["dispatcher"])

            warn_missing_config_keys = ["input", "sim", "network"]
            for key in warn_missing_config_keys:
                if key not in conf:
                    log.warning(f"scenario file is missing a '{key}' section may cause errors")

            sconfig = Sim.build(conf.get("sim"))
            iconfig = Input.build(conf.get("input"), scenario_file_path, conf.get("cache"))
            nconfig = Network.build(conf.get("network"))
            dconfig = DispatcherConfig.build(conf.get("dispatcher"))

            if output_suffix is None:
                output_suffix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            scenario_name = sconfig.sim_name + "_" + output_suffix
            scenario_output_directory = Path(global_config.output_base_directory) / Path(
                scenario_name
            )

            hive_config = HiveConfig(
                global_config=global_config,
                input_config=iconfig,
                sim=sconfig,
                network=nconfig,
                dispatcher=dconfig,
                scenario_output_directory=scenario_output_directory,
            )

            if global_config.verbose:
                log.info(f"output directory set to {hive_config.input_config.scenario_directory}")
                log.info(f"hive config loaded from {str(scenario_file_path)}")
                log.info(f"\n{yaml.dump(conf)}")

            return hive_config

    def asdict(self) -> Dict:
        out_dict = {}
        cache = {}
        input_configuration = self.input_config.asdict()

        for name, value in input_configuration.items():
            if not value:
                continue
            else:
                path = Path(value)
                if not path.is_file():
                    continue
                else:
                    with path.open(mode="rb") as f:
                        data = f.read()
                        md5_sum = hashlib.md5(data).hexdigest()
                        cache[name] = md5_sum
        out_dict["cache"] = cache

        for name, config in self._asdict().items():
            if issubclass(config.__class__, tuple):
                out_dict[name] = config.asdict()
            else:
                out_dict[name] = config

        return out_dict

    def set_scenario_output_directory(self, output_directory: Path) -> HiveConfig:
        return self._replace(scenario_output_directory=output_directory)

    def suppress_logging(self) -> HiveConfig:
        updated_gconfig = self.global_config._replace(
            log_run=False,
            log_states=False,
            log_events=False,
            log_kepler=False,
            log_stats=False,
            log_station_capacities=False,
            log_instructions=False,
            log_time_step_stats=False,
            log_fleet_time_step_stats=False,
        )
        return self._replace(global_config=updated_gconfig)

    def to_yaml(self):
        """
        writes this configuration as a file in the scenario output directory
        """
        config_dump = self.asdict()
        dump_name = self.sim.sim_name + ".yaml"
        dump_path = os.path.join(self.scenario_output_directory, dump_name)
        with open(dump_path, "w") as f:
            yaml.dump(config_dump, f, sort_keys=False)
