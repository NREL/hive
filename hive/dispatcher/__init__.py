__doc__ = """
dispatchers assign requests to vehicles and reposition unassigned vehicles
"""
import hive.dispatcher.forecaster
import hive.dispatcher.manager
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.managed_dispatcher import ManagedDispatcher
from hive.dispatcher.manager import BasicManager
from hive.dispatcher.forecaster import BasicForecaster
from hive.config import HiveConfig


def default_dispatcher(config: HiveConfig) -> DispatcherInterface:
    manager = BasicManager(demand_forecaster=BasicForecaster())
    dispatcher = ManagedDispatcher.build(
        manager=manager,
        geofence_file=config.io.geofence_file,
    )
    return dispatcher
