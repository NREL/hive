from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from typing import NamedTuple, Dict, Union, Tuple

from hive.config import *
from hive.config.dispatcher_config import DispatcherConfig

log = logging.getLogger(__name__)


class HiveConfig(NamedTuple):
    io: IO
    sim: Sim
    network: Network
    dispatcher: DispatcherConfig

    init_time: str

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, HiveConfig]:
        return ConfigBuilder.build(
            default_config={},
            required_config=(),
            config_constructor=lambda c: HiveConfig.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[Exception, HiveConfig]:
        hive_config = HiveConfig(
            io=IO.build(d.get('io'), d.get('cache')),
            sim=Sim.build(d.get('sim')),
            network=Network.build(d.get('network')),
            dispatcher=DispatcherConfig.build(d.get('dispatcher')),
            init_time=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

        # check to see if the dispatcher update interval is in line with the time step interval
        time_steps = range(
            hive_config.sim.start_time,
            hive_config.sim.end_time,
            hive_config.sim.timestep_duration_seconds,
        )
        d_interval = hive_config.dispatcher.default_update_interval_seconds
        l_interval = hive_config.io.progress_period_seconds
        p_interval = hive_config.io.log_period_seconds
        if not any(s % d_interval == 0 for s in time_steps):
            # TODO: Add documentation to explain why this would be an issue.
            log.warning(f"the default_update_interval of {d_interval} seconds is not in line with the time steps")
        if not any(s % d_interval == 0 for s in time_steps):
            log.warning(f"the log_period of {l_interval} seconds is not in line with the time steps")
        if not any(s % d_interval == 0 for s in time_steps):
            log.warning(f"the progress_period of {p_interval} is not in line with the time steps")

        return hive_config

    def asdict(self) -> Dict:
        out_dict = {}
        cache = {}

        for name, value in self.io.file_paths.asdict(absolute_paths=True).items():
            if not value:
                continue
            with open(value, 'rb') as f:
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
    def output_directory(self) -> str:
        run_name = self.sim.sim_name + '_' + self.init_time
        output_directory = os.path.join(self.io.working_directory, run_name)
        return output_directory
