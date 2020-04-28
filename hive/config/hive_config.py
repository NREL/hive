from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import NamedTuple, Dict, Union, Tuple

from hive.config.config_builder import ConfigBuilder
from hive.config.dispatcher_config import DispatcherConfig
from hive.config.network import Network
from hive.config.io import IO
from hive.config.sim import Sim
from hive.config.system import System


class HiveConfig(NamedTuple):
    system: System
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
        return HiveConfig(
            system=System.build(d.get('system')),
            io=IO.build(d.get('io'), d.get('cache')),
            sim=Sim.build(d.get('sim')),
            network=Network.build(d.get('network')),
            dispatcher=DispatcherConfig.build(d.get('dispatcher')),
            init_time=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

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
