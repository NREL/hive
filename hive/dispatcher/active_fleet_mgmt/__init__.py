__doc__ = """
HIVE Repositioning Module

provides a specification and a delivery method for repositioning implementations into a simulation.

defining new repositioning modules requires
1. creating a class which inherits from AbstractRepositioning,
2. "registering" the class by adding it to the '_valid_repositioning' dictionary in repositioning.py
"""

from hive.dispatcher.active_fleet_mgmt.abstract_active_fleet_mgmt import AbstractActiveFleetMgmt
from hive.dispatcher.active_fleet_mgmt.basic_active_mgmt import BasicActiveMgmt
from hive.dispatcher.active_fleet_mgmt.random_repositioning import RandomRepositioning
__all__ = [
    "AbstractActiveFleetMgmt",
    "RandomRepositioning",
    "BasicActiveMgmt",
    ]
