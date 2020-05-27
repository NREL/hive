from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Dict, Union, Tuple

from hive.config.config_builder import ConfigBuilder
from hive.config.dispatcher_config import DispatcherConfig
from hive.config.global_config import GlobalConfig
from hive.config.input import Input
from hive.config.network import Network
from hive.config.sim import Sim
from hive.util import fs

log = logging.getLogger(__name__)


class HiveConfig(NamedTuple):
    global_config: GlobalConfig
    input: Input
    sim: Sim
    network: Network
    dispatcher: DispatcherConfig

    out_dir_time: str

    @classmethod
    def build(cls, scenario_file_path: Path, config: Dict = None) -> Union[Exception, HiveConfig]:
        return ConfigBuilder.build(
            default_config={},
            required_config=(),
            config_constructor=lambda c: HiveConfig.from_dict(c, scenario_file_path),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict, scenario_file_path: Path) -> Union[Exception, HiveConfig]:
        warn_missing_config_keys = ['input', 'sim', 'network']
        for key in warn_missing_config_keys:
            if key not in d:
                log.warning(f"scenario file is missing a '{key}' section may cause errors")

        hive_config = HiveConfig(
            global_config=fs.global_hive_config_search(),
            input=Input.build(d.get('input'), scenario_file_path, d.get('cache')),
            sim=Sim.build(d.get('sim')),
            network=Network.build(d.get('network')),
            dispatcher=DispatcherConfig.build(d.get('dispatcher')),
            out_dir_time=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

        # check to see if the dispatcher update interval is in line with the time step interval
        time_steps = range(
            hive_config.sim.start_time,
            hive_config.sim.end_time,
            hive_config.sim.timestep_duration_seconds,
        )
        d_interval = hive_config.dispatcher.default_update_interval_seconds
        p_interval = hive_config.global_config.log_period_seconds
        if not any(s % d_interval == 0 for s in time_steps):
            # TODO: Add documentation to explain why this would be an issue.
            log.warning(f"the default_update_interval of {d_interval} seconds is not in line with the time steps")
        if not any(s % p_interval == 0 for s in time_steps):
            log.warning(f"the progress_period of {p_interval} is not in line with the time steps")

        return hive_config

    def asdict(self) -> Dict:
        out_dict = {}
        cache = {}
        input_configuration = self.input.asdict()

        for name, value in input_configuration.items():
            if not value:
                continue
            else:
                path = Path(value)
                if not path.is_file():
                    continue
                else:
                    with path.open(mode='rb') as f:
                        data = f.read()
                        md5_sum = hashlib.md5(data).hexdigest()
                        cache[name] = md5_sum
        out_dict['cache'] = cache

        for name, config in self._asdict().items():
            if issubclass(config.__class__, Tuple):
                out_dict[name] = config.asdict()
            else:
                out_dict[name] = config

        return out_dict

    @property
    def scenario_output_directory(self) -> str:
        run_name = self.sim.sim_name + '_' + self.out_dir_time
        output_directory = os.path.join(self.global_config.output_base_directory, run_name)
        return output_directory

