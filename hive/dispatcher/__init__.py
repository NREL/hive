__doc__ = """
HIVE Dispatcher Module

provides a specification and a delivery method for dispatcher implementations into a simulation.

defining new dispatchers requires 
1. creating a class which inherits from AbstractDispatcher,
2. "registering" the class by adding it to the '_valid_dispatchers' dictionary in dispatcher.py 
"""
from hive.dispatcher.abstractdispatcher import AbstractDispatcher
from hive.dispatcher.greedydispatcher import GreedyDispatcher
__all__ = ["AbstractDispatcher", "GreedyDispatcher"]