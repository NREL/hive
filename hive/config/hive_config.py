from __future__ import annotations

import os
from datetime import datetime
from typing import NamedTuple, Dict, Union

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

    @property
    def output_directory(self) -> str:
        run_name = self.sim.sim_name + '_' + self.init_time
        output_directory = os.path.join(self.io.working_directory, run_name)
        return output_directory
