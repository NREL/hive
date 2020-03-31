from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

import immutables
from pkg_resources import resource_filename

from hive.config.hive_config import HiveConfig
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.forecaster import BasicForecaster
from hive.dispatcher.managers.base_management import BaseManagement
from hive.dispatcher.managers.basic_charging import BasicCharging
from hive.dispatcher.managers.fleet_position import FleetPosition
from hive.dispatcher.managers.greedy_matching import GreedyMatcher
from hive.util.helpers import DictOps

if TYPE_CHECKING:
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.dispatcher.managers.manager_interface import ManagerInterface
    from hive.util.typealiases import Report


log = logging.getLogger(__name__)


class BasicDispatcher(NamedTuple, DispatcherInterface):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """
    managers: Tuple[ManagerInterface, ...]

    @classmethod
    def build(cls, config: HiveConfig) -> BasicDispatcher:
        """
        builds a basic dispatcher from a config
        :param config: the scenario config
        :return: a BasicDispatcher
        """
        demand_forecast_file = resource_filename("hive.resources.demand_forecast", config.io.demand_forecast_file)

        # this ordering is important as the later managers will override any instructions from the previous managers
        # for a specific vehicle id.
        managers = (
            BaseManagement(config.dispatcher.base_vehicles_charging_limit),
            FleetPosition(
                demand_forecaster=BasicForecaster.build(demand_forecast_file),
                update_interval_seconds=config.dispatcher.fleet_sizing_update_interval_seconds
            ),
            BasicCharging(config.dispatcher.charging_low_soc_threshold),
            GreedyMatcher(config.dispatcher.matching_low_soc_threshold),
        )
        dispatcher = BasicDispatcher(
            managers=managers,
        )
        return dispatcher

    def generate_instructions(self,
                              simulation_state: 'SimulationState',
                              ) -> Tuple[DispatcherInterface, InstructionMap, Tuple[Report, ...]]:

        instruction_map = immutables.Map()
        reports = ()
        updated_managers = ()

        for manager in self.managers:

            new_manager, new_instructions, manager_reports = manager.generate_instructions(simulation_state)

            reports = reports + manager_reports

            for instruction in new_instructions:
                instruction_map = DictOps.add_to_dict(instruction_map, instruction.vehicle_id, instruction)

            updated_managers = updated_managers + (new_manager,)

        return self._replace(managers=updated_managers), instruction_map, reports
