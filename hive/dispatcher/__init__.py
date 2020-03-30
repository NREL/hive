__doc__ = """
dispatchers assign requests to vehicles and reposition unassigned vehicles
"""
from pkg_resources import resource_filename

import hive.dispatcher.forecaster
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.managers.base_management import BaseManagement
from hive.dispatcher.managers.greedy_matching import GreedyMatcher
from hive.dispatcher.managers.basic_charging import BasicCharging
from hive.dispatcher.managers.fleet_position import FleetPosition
from hive.dispatcher.basic_dispatcher import BasicDispatcher
from hive.dispatcher.forecaster import BasicForecaster
from hive.config import HiveConfig


def default_dispatcher(config: HiveConfig) -> DispatcherInterface:
    demand_forecast_file = resource_filename("hive.resources.demand_forecast", config.io.demand_forecast_file)

    # this ordering is important as the later managers will override any instructions from the previous managers
    # for a specific vehicle id.
    managers = (
        BaseManagement(),
        FleetPosition(demand_forecaster=BasicForecaster.build(demand_forecast_file)),
        BasicCharging(),
        GreedyMatcher(),
    )
    dispatcher = BasicDispatcher(
        managers=managers,
    )
    return dispatcher
