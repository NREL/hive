from hive.dispatcher.inactive_fleet_mgmt import (
    AbstractInactiveMgmt,
    BasicInactiveMgmt,
    )

"""
the list of valid string names for dispatchers which can be
requested in the scenario file
"""
_valid_inactive_module = {
    "basic": BasicInactiveMgmt,
}

def from_scenario_input(
                    name,
                    fleet,
                    fleet_state,
                    env_params,
                    clock,
                    ):
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
        inactive_module = _valid_inactive_module[name.lower()](
                                                        fleet,
                                                        fleet_state,
                                                        env_params,
                                                        clock,
                                                    )
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_inactive_module.keys()])
        raise ModuleNotFoundError("Inactive module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(inactive_module), AbstractInactiveMgmt)
    return inactive_module
