import logging

from hive.dispatcher.assignment.abstractassignment import AbstractAssignment
from hive.dispatcher.assignment.greedyassignment import GreedyAssignment

log = logging.getLogger(__name__)

"""
the list of valid string names for assignment modules which can be
requested in the scenario file
"""
_valid_assignment_modules = {
    "greedy": GreedyAssignment
}


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
        assignment_module = _valid_assignment_modules[name.lower()]()
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_assignment_modules.keys()])
        log.error("'{}' not one of valid dispatcher names: {}".format(name, valid_keys))
        raise ModuleNotFoundError("Assignment module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(assignment_module), AbstractAssignment)
    return assignment_module
