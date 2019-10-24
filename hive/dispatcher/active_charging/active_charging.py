from hive.dispatcher.active_charging import AbstractCharging, BasicCharging

"""
the list of valid string names for assignment modules which can be
requested in the scenario file
"""
_valid_charging_modules = {
    "basic": BasicCharging
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
        charging_module = _valid_charging_modules[name.lower()](
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
        valid_keys = ", ".join([k for k in _valid_charging_modules.keys()])
        raise ModuleNotFoundError("charging module '{}' not found".format(name))
    # this enforces class inheritance
    assert issubclass(type(charging_module), AbstractCharging)
    return charging_module
