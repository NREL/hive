from hive.dispatcher.inactive_fleet_mgmt import inactive_fleet_mgmt
from hive.dispatcher.active_fleet_mgmt import active_fleet_mgmt
from hive.dispatcher.active_servicing import active_servicing
from hive.dispatcher.active_charging import active_charging
from hive.vehiclestate import VehicleState
from hive.charging import find_closest_plug

import numpy as np
import random

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
        self._fleet = fleet
        self._fleet_state = fleet_state
        self._stations  = stations
        self._bases = bases
        self._route_engine = route_engine
        self._ENV = env_params

    def _deactivate_vehicles(self, n):
        fleet_state = self._fleet_state

        veh_ste_col = self._ENV['FLEET_STATE_IDX']['vehicle_state']
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']

        soc_sorted = np.argsort(fleet_state[:, soc_col])

        idle_veh_mask = (fleet_state[:, veh_ste_col] == VehicleState.IDLE.value) \
            | (fleet_state[:, veh_ste_col] == VehicleState.REPOSITIONING.value)

        veh_ids = soc_sorted[idle_veh_mask[soc_sorted]][:abs(n)]

        for veh_id in veh_ids:
            veh = self._fleet[veh_id]
            base = find_closest_plug(veh, self._bases)

            route_summary = self._route_engine.route(veh.lat, veh.lon,
                                                     base.LAT, base.LON,
                                                     VehicleState.DISPATCH_BASE)
            route = route_summary['route']
            veh.cmd_return_to_base(base, route)


    def _activate_vehicles(self, n):
        fleet_state = self._fleet_state

        veh_ste_col = self._ENV['FLEET_STATE_IDX']['vehicle_state']
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']

        soc_sorted = np.argsort(-fleet_state[:, soc_col])

        veh_mask = (fleet_state[:, veh_ste_col] == VehicleState.CHARGING_BASE.value) \
            | (fleet_state[:, veh_ste_col] == VehicleState.RESERVE_BASE.value)

        veh_ids = soc_sorted[veh_mask[soc_sorted]][:n]

        for veh_id in veh_ids:
            veh = self._fleet[veh_id]

            veh.cmd_unplug()
            veh.vehicle_state = VehicleState.IDLE


    def balance_fleet(self, active_fleet_target):

        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()

        n = active_fleet_target - active_vehicles

        self.active_fleet_target = active_fleet_target

        if n > 0:
            self._activate_vehicles(n)
        elif n < 0:
            self._deactivate_vehicles(n)



    def step(self, requests):
        self.active_servicing_module.process_requests(requests)
        self.active_fleet_mgmt_module.reposition_agents()
        self.active_charging_module.charge()
        self.inactive_fleet_mgmt_module.manage_inactive_fleet()
