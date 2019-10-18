from hive.dispatcher.inactive_fleet_mgmt import AbstractInactiveMgmt
from hive.vehiclestate import VehicleState

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


    def manage_inactive_fleet(self):
        """
        """
        pass


    def log(self):
        """
        the best algorithms do no logging
        """
        pass
