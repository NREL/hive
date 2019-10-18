from hive.dispatcher.inactive_fleet_mgmt import inactive_fleet_mgmt
from hive.dispatcher.active_fleet_mgmt import active_fleet_mgmt
from hive.dispatcher.active_servicing import active_servicing
from hive.dispatcher.active_charging import active_charging

class Dispatcher:
    def __init__(
            self,
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
        #TODO: Considering combining module input params into a single data structure
        self.inactive_fleet_mgmt_module = inactive_fleet_mgmt.from_scenario_input(
                                                                    inactive_fleet_mgmt_name,
                                                                    fleet,
                                                                    fleet_state,
                                                                    env_params,
                                                                    clock,
                                                                    )
        self.active_fleet_mgmt_module = active_fleet_mgmt.from_scenario_input(
                                                                    active_fleet_mgmt_name,
                                                                    fleet,
                                                                    fleet_state,
                                                                    stations,
                                                                    bases,
                                                                    demand,
                                                                    env_params,
                                                                    route_engine,
                                                                    clock,
                                                                    )
        self.active_servicing_module = active_servicing.from_scenario_input(
                                                                    active_servicing_name,
                                                                    fleet,
                                                                    fleet_state,
                                                                    stations,
                                                                    bases,
                                                                    demand,
                                                                    env_params,
                                                                    route_engine,
                                                                    clock,
                                                                    log,
                                                                    )
        self.active_charging_module = active_charging.from_scenario_input(
                                                                    active_charging_name,
                                                                    fleet,
                                                                    fleet_state,
                                                                    stations,
                                                                    bases,
                                                                    demand,
                                                                    env_params,
                                                                    route_engine,
                                                                    clock,
                                                                    )

    def balance_fleet(self, fleet_differential):
        pass

    def step(self, requests):
        self.active_servicing_module.process_requests(requests)
        self.active_fleet_mgmt_module.reposition_agents()
        self.active_charging_module.charge()
        self.inactive_fleet_mgmt_module.manage_inactive_fleet()
