__doc__ = """
Fleet manager forecasts demand and sends fleet differential signal to dispatcher
"""
from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.dispatcher.manager.fleet_target import StateTarget, VehicleStateSet, FleetStateTarget
from hive.dispatcher.manager.basic_manager import BasicManager
