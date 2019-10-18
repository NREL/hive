__doc__ = """
HIVE Inactive Fleet Management Module

provides a specification and a delivery method for repositioning implementations into a simulation.

defining new repositioning modules requires
1. creating a class which inherits from AbstractRepositioning,
2. "registering" the class by adding it to the '_valid_repositioning' dictionary in repositioning.py
"""

from hive.dispatcher.inactive_fleet_mgmt.abstract_inactive import AbstractInactiveMgmt
from hive.dispatcher.inactive_fleet_mgmt.basic_inactive import BasicInactiveMgmt
__all__ = [
    "AbstractInactiveMgmt",
    "BasicInactiveMgmt",
    ]
