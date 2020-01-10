import random

from typing import Tuple

from hive.state.simulation_state import SimulationState
from hive.manager.manager import Manager
from hive.manager.fleet_target import StateTarget, FleetStateTarget
from hive.model.vehiclestate import VehicleState


class BasicManager(Manager):
    """
    A class that computes an optimal fleet state.
    """

    def generate_fleet_target(self, simulation_state: SimulationState) -> Tuple[Manager, FleetStateTarget]:
        """
        Generate fleet targets to be consumed by the dispatcher.

        :param simulation_state: The current simulation state
        :return: the update Manager along with the fleet target
        """
        active_set = frozenset({
            VehicleState.IDLE,
            VehicleState.SERVICING_TRIP,
            VehicleState.DISPATCH_TRIP,
            VehicleState.DISPATCH_STATION,
            VehicleState.CHARGING_STATION,
            VehicleState.REPOSITIONING,
        })

        active_target = StateTarget(id='ACTIVE',
                                    state_set=active_set,
                                    n_vehicles=random.randint(1, 100))

        fleet_state_target = {active_target.id: active_target}

        return self, fleet_state_target
