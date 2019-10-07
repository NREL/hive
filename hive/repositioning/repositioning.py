import logging

from hive.repositioning.abstractrepositioning import AbstractRepositioning
from hive.repositioning.donothingrepositioning import DoNothingRepositioning

log = logging.getLogger(__name__)

"""
the list of valid string names for dispatchers which can be
requested in the scenario file
"""
_valid_repositioning = {
    "do_nothing": DoNothingRepositioning
}


def from_scenario_input(name):
    """
    takes a string name and attempts to use it to load a dispatcher

    Parameters
    ----------
    name
        name of a repositioning module (case insensitive)
    Returns
    -------
    AbstractRepositioning
        a subclass of AbstractRepositioning, or throws a ModuleNotFoundError

    Raises
    ------
    ModuleNotFoundError
        when an invalid module name is provided
    AssertionError
        when the module created does not inherit correctly from AbstractRepositioning
    """
    try:
        repositioning = _valid_repositioning[name.lower()]()
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_repositioning.keys()])
        log.error("'{}' not one of valid repositioning module names: {}".format(name, valid_keys))
        raise ModuleNotFoundError("Repositioning module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(repositioning), AbstractRepositioning)
    return repositioning


