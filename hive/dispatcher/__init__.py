__doc__ = """
dispatchers assign requests to vehicles and reposition unassigned vehicles
"""
from pkg_resources import resource_filename

import hive.dispatcher.forecaster
import hive.dispatcher.manager
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.instructors.greedy_matching import GreedyMatcher
from hive.dispatcher.instructors.basic_charging import BasicCharging
from hive.dispatcher.basic_dispatcher import BasicDispatcher
from hive.dispatcher.manager import BasicManager
from hive.dispatcher.forecaster import BasicForecaster
from hive.config import HiveConfig


def default_dispatcher(config: HiveConfig) -> DispatcherInterface:
    demand_forecast_file = resource_filename("hive.resources.demand_forecast", config.io.demand_forecast_file)
    manager = BasicManager(demand_forecaster=BasicForecaster.build(demand_forecast_file))
    instructors = (GreedyMatcher(), BasicCharging())
    dispatcher = BasicDispatcher.build(
        manager=manager,
        instructors=instructors,
    )
    return dispatcher
