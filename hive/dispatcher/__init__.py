__doc__ = """
dispatchers assign requests to vehicles and reposition unassigned vehicles
"""
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.managers.base_management import BaseManagement
from hive.dispatcher.managers.greedy_matching import GreedyMatcher
from hive.dispatcher.managers.basic_charging import BasicCharging
from hive.dispatcher.managers.fleet_position import FleetPosition
from hive.dispatcher.basic_dispatcher import BasicDispatcher
from hive.dispatcher.forecaster import BasicForecaster
