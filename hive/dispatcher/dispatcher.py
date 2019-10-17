from hive.dispatcher.inactive_fleet_mgmt import inactive_fleet_mgmt
from hive.dispatcher.active_fleet_mgmt import active_fleet_mgmt
from hive.dispatcher.active_servicing import active_servicing
from hive.dispatcher.active_charging import active_charging

class Dispatcher:
    def __init__(
            inactive_fleet_mgmt_name,
            active_fleet_mgmt_name,
            active_servicing_name,
            active_charging_name,
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
        :param inactive_fleet_mgmt_name,
        :param active_fleet_mgmt_name,
        :param active_servicing_name,
        :param active_charging_name,
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
        self.inactive_fleet_mgmt_module = inactive_fleet_mgmt.from_scenario_input(inactive_fleet_mgmt_name)
        self.active_fleet_mgmt_module = active_fleet_mgmt.from_scenario_input(active_fleet_mgmt_name)
        self.active_servicing_module = active_servicing.from_scenario_input(active_servicing_name)
        self.active_charging_module = active_charging.from_scenario_input(active_charging_name)
