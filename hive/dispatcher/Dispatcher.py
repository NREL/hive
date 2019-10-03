import logging

from hive.dispatcher.AbstractDispatcher import AbstractDispatcher
from hive.dispatcher.GreedyDispatcher import GreedyDispatcher

log = logging.getLogger(__name__)

"""
the list of valid string names for dispatchers which can be
requested in the scenario file
"""
_valid_dispatchers = {
    "greedy": GreedyDispatcher
}


def from_scenario_input(name):
    """
    takes a string name and attempts to use it to load a dispatcher

    Parameters
    ----------
    name
        name of a Dispatcher module (case insensitive)
    Returns
    -------
    AbstractDispatcher
        a subclass of AbstractDispatcher, or throws a ModuleNotFoundError

    Raises
    ------
    ModuleNotFoundError
        when an invalid module name is provided
    AssertionError
        when the module created does not inherit correctly from AbstractDispatcher
    """
    try:
        dispatcher = _valid_dispatchers[name.lower()]()
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_dispatchers.keys()])
        log.error("'{}' not one of valid dispatcher names: {}".format(name, valid_keys))
        raise ModuleNotFoundError("Dispatcher module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(dispatcher), AbstractDispatcher)
    return dispatcher

