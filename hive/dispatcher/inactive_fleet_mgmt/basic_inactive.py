from hive.dispatcher.inactive_fleet_mgmt import AbstractInactiveMgmt
from hive.vehiclestate import VehicleState

import numpy as np

class BasicInactiveMgmt(AbstractInactiveMgmt):
    """
    Simple active fleet management that lets vehicles time out.
    """

    def __init__(
            self,
            fleet,
            fleet_state,
            env_params,
            clock,
            ):
        super().__init__(
                    fleet,
                    fleet_state,
                    env_params,
                    clock,
                )


    def manage_inactive_charging(self):
        """
        """
        pass

    def activate_vehicles(self, active_fleet_target):
        """
        """
        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()

        n = active_fleet_target - active_vehicles

        if n <= 0:
            return

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


    def log(self):
        """
        the best algorithms do no logging
        """
        pass
