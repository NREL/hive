__doc__ = """
HIVE Charging Module

provides a specification and a delivery method for dispatcher assignment implementations into a simulation.

defining new assignment modules requires
1. creating a class which inherits from AbstractCharging,
2. "registering" the class by adding it to the '_valid_assignment_modules' dictionary in active_charging.py
"""
from hive.dispatcher.active_charging.abstract_charging import AbstractCharging
from hive.dispatcher.active_charging.basic_charging import BasicCharging

__all__ = ["AbstractCharging", "BasicCharging"]
