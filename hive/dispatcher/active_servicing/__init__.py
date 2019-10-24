__doc__ = """
HIVE Assignment Module

provides a specification and a delivery method for dispatcher assignment implementations into a simulation.

defining new assignment modules requires
1. creating a class which inherits from AbstractAssignment,
2. "registering" the class by adding it to the '_valid_assignment_modules' dictionary in assignment.py
"""
from hive.dispatcher.active_servicing.abstract_servicing import AbstractServicing
from hive.dispatcher.active_servicing.greedy_assignment import GreedyAssignment

__all__ = ["AbstractServicing", "GreedyAssignment"]
