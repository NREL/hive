__doc__ = """
dispatchers assign requests to vehicles and reposition unassigned vehicles
"""
from hive.dispatcher.forecaster import BasicForecaster
from hive.dispatcher.instruction_generator.base_fleet_manager import BaseFleetManager
from hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.dispatcher.instruction_generator.position_fleet_manager import PositionFleetManager
