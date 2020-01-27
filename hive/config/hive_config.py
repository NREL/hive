from __future__ import annotations

from datetime import datetime

from typing import NamedTuple, Dict, Union, Optional

from hive.config import ConfigBuilder, Output, Sim, Network, Scenario


class HiveConfig(NamedTuple):
    io: Optional[Output]
    sim: Optional[Sim]
    network: Optional[Network]
    scenario: Optional[Scenario]

    timestamp: str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, HiveConfig]:
        return ConfigBuilder.build(
            default_config={},
            required_config={},
            config_constructor=lambda c: HiveConfig.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[Exception, HiveConfig]:
        io_build = Output.build(d['io']) if 'io' in d else None
        sim_build = Sim.build(d['sim']) if 'sim' in d else None
        network_build = Network.build(d['network']) if 'network' in d else None
        scenario_build = Scenario.build(d['scenario']) if 'scenario' in d else None

        if isinstance(io_build, Exception):
            return io_build
        elif isinstance(sim_build, Exception):
            return sim_build
        elif isinstance(network_build, Exception):
            return network_build
        elif isinstance(scenario_build, Exception):
            return scenario_build
        else:
            return HiveConfig(
                io=io_build,
                sim=sim_build,
                network=network_build,
                scenario=scenario_build
            )

    def run_name(self) -> str:
        sim_name: str = self.sim.sim_name if self.sim else ""
        return sim_name + '_' + self.timestamp
