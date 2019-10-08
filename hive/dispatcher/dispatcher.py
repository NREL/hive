from hive.dispatcher.combined import combined
from hive.dispatcher.assignment import assignment
from hive.dispatcher.repositioning import repositioning


def load_dispatcher(
        assignment_module_name,
        repositioning_module_name,
        fleet,
        fleet_state,
        stations,
        bases,
        demand,
        env_params,
        route_engine,
        clock,
        log,
):
    """

    :param assignment_module_name:
    :param repositioning_module_name:
    :param fleet:
    :param fleet_state:
    :param stations:
    :param bases:
    :param demand:
    :param env_params:
    :param route_engine:
    :param clock:
    :return:
    """
    assignment_module, repositioning_module, module_type = _get_modules(assignment_module_name, repositioning_module_name)

    assignment_module.spin_up(
        fleet=fleet,
        fleet_state=fleet_state,
        stations=stations,
        bases=bases,
        demand=demand,
        env_params=env_params,
        route_engine=route_engine,
        clock=clock,
        log=log)

    if module_type != "combined":
        # only spin_up the repositioning module if it is not the same
        # object as the assignment module - only need to construct it
        # once!
        repositioning_module.spin_up(
            fleet=fleet,
            fleet_state=fleet_state,
            stations=stations,
            bases=bases,
            demand=demand,
            env_params=env_params,
            route_engine=route_engine,
            clock=clock,
            log=log,
        )

    return assignment_module, repositioning_module


def _get_modules(assignment_module_name, repositioning_module_name):
    if assignment_module_name == repositioning_module_name and combined.module_exists(assignment_module_name):
        combined_module = combined.from_scenario_input(assignment_module_name)
        return combined_module, combined_module, "combined"
    else:
        assignment_module = assignment.from_scenario_input(assignment_module_name)
        repositioning_module = repositioning.from_scenario_input(repositioning_module_name)
        return assignment_module, repositioning_module, ""
