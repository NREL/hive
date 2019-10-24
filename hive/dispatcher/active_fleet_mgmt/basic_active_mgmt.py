from hive.dispatcher.active_fleet_mgmt import AbstractActiveFleetMgmt
from hive.charging import find_closest_plug
from hive.vehiclestate import VehicleState

import numpy as np


class BasicActiveMgmt(AbstractActiveFleetMgmt):
    """
    the laziest replanner, assumes that everything's gonna be great.
    """

    def __init__(
            self,
            fleet,
            fleet_state,
            stations,
            bases,
            demand,
            env_params,
            route_engine,
            clock,
            ):
        super().__init__(
                    fleet,
                    fleet_state,
                    stations,
                    bases,
                    demand,
                    env_params,
                    route_engine,
                    clock,
                    )

    def reposition_agents(self):
        """
        does nothing!
        """
        pass

    def deactivate_vehicles(self, active_fleet_target):
        """
        makes decisions related to deactivating vehicles at each time step
        """
        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()

        n = active_fleet_target - active_vehicles

        if n >= 0:
            return

        fleet_state = self._fleet_state

        veh_ste_col = self._ENV['FLEET_STATE_IDX']['vehicle_state']
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']

        soc_sorted = np.argsort(fleet_state[:, soc_col])

        idle_veh_mask = (fleet_state[:, veh_ste_col] == VehicleState.IDLE.value) \
            | (fleet_state[:, veh_ste_col] == VehicleState.REPOSITIONING.value)

        idle_min_col = self._ENV['FLEET_STATE_IDX']['idle_min']
        idle_min_mask = self._fleet_state[:, idle_min_col] >= self._ENV['MAX_ALLOWABLE_IDLE_MINUTES']

        mask = idle_veh_mask & idle_min_mask

        veh_ids = soc_sorted[mask[soc_sorted]][:abs(n)]

        for veh_id in veh_ids:
            veh = self._fleet[veh_id]
            base = find_closest_plug(veh, self._bases)

            route_summary = self._route_engine.route(veh.lat, veh.lon,
                                                     base.LAT, base.LON,
                                                     VehicleState.DISPATCH_BASE)
            route = route_summary['route']
            veh.cmd_return_to_base(base, route)

    def log(self):
        """
        the best algorithms do no logging
        """
        pass
