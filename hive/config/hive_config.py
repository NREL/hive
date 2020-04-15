from __future__ import annotations

import os
from datetime import datetime
from typing import NamedTuple, Dict, Union, Optional, Tuple

import yaml

from hive.config import *
from hive.config.dispatcher_config import DispatcherConfig


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
        return HiveConfig(
            io=IO.build(d.get('io')),
            sim=Sim.build(d.get('sim')),
            network=Network.build(d.get('network')),
            dispatcher=DispatcherConfig.build(d.get('dispatcher')),
            init_time=datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

    def dump(self, file_path: Optional[str] = None):
        if not file_path:
            file_name = self.sim.sim_name + ".yaml"
            file_path = os.path.join(self.output_directory, file_name)

        out_dict = {}
        for name, config in self._asdict().items():
            if issubclass(config.__class__, Tuple):
                out_dict[name] = config._asdict()
            else:
                out_dict[name] = config

        with open(file_path, 'w') as f:
            yaml.dump(out_dict, f, sort_keys=False)

    @property
    def output_directory(self) -> str:
        run_name = self.sim.sim_name + '_' + self.init_time
        output_directory = os.path.join(self.io.working_directory, run_name)
        return output_directory
