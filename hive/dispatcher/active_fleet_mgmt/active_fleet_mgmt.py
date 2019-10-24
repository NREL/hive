from hive.dispatcher.active_fleet_mgmt import (
    AbstractActiveFleetMgmt,
    RandomRepositioning,
    BasicActiveMgmt,
    )

"""
the list of valid string names for dispatchers which can be
requested in the scenario file
"""
_valid_repositioning = {
    "random": RandomRepositioning,
    "basic": BasicActiveMgmt,
}


def from_scenario_input(
                    name,
                    fleet,
                    fleet_state,
                    stations,
                    bases,
                    demand,
                    env_params,
                    route_engine,
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
        repositioning = _valid_repositioning[name.lower()](
                                                    fleet,
                                                    fleet_state,
                                                    stations,
                                                    bases,
                                                    demand,
                                                    env_params,
                                                    route_engine,
                                                    clock,
                                                    )
    except KeyError:
        valid_keys = ", ".join([k for k in _valid_repositioning.keys()])
        raise ModuleNotFoundError("Repositioning module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(repositioning), AbstractActiveFleetMgmt)
    return repositioning
