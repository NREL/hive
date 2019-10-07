import logging

from hive.dispatcher.combined.abstractcombined import AbstractCombined
from hive.dispatcher.combined.donothingatall import DoNothingAtAll

log = logging.getLogger(__name__)

"""
the list of valid string names for combined assignment/repositioning modules which can be
requested in the scenario file
"""
_valid_combined_modules = {
    "do_nothing": DoNothingAtAll
}


def module_exists(name):
    return name in _valid_combined_modules


def from_scenario_input(name):
    """
    takes a string name and attempts to use it to load an assignment module

    Parameters
    ----------
    name
        name of an assignment module (case insensitive)
    Returns
    -------
    AbstractAssignment
        a subclass of AbstractAssignment, or throws a ModuleNotFoundError

    Raises
    ------
    ModuleNotFoundError
        when an invalid module name is provided
    AssertionError
        when the module created does not inherit correctly from AbstractAssignment
    """
    try:
        combined_module = _valid_combined_modules[name.lower()]()
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_combined_modules.keys()])
        log.error("'{}' not one of valid dispatcher names: {}".format(name, valid_keys))
        raise ModuleNotFoundError("Combined module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(combined_module), AbstractCombined)
    return combined_module
