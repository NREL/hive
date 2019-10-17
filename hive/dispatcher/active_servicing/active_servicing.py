from hive.dispatcher.active_servicing.abstract_servicing import AbstractServicing
from hive.dispatcher.active_servicing.greedy_assignment import GreedyAssignment

"""
the list of valid string names for assignment modules which can be
requested in the scenario file
"""
_valid_servicing_modules = {
    "greedy": GreedyAssignment
}


def from_scenario_input(name):
    """
    takes a string name and attempts to use it to load an servicing module

    Parameters
    ----------
    name
        name of an servicing module (case insensitive)
    Returns
    -------
    AbstractServicing
        a subclass of AbstractServicing, or throws a ModuleNotFoundError

    Raises
    ------
    ModuleNotFoundError
        when an invalid module name is provided
    AssertionError
        when the module created does not inherit correctly from AbstractServicing
    """
    try:
        servicing_module = _valid_servicing_modules[name.lower()]()
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_servicing_modules.keys()])
        log.error("'{}' not one of valid dispatcher names: {}".format(name, valid_keys))
        raise ModuleNotFoundError("servicing module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(servicing_module), AbstractServicing)
    return servicing_module
