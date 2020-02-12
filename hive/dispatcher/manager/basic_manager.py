from __future__ import annotations

from typing import Tuple, NamedTuple

from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.dispatcher.manager.fleet_target import StateTarget, FleetStateTarget
from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.model.vehiclestate import VehicleState


class BasicManager(NamedTuple, ManagerInterface):
    """
    A class that computes an optimal fleet state.
    """
    demand_forecaster: ForecasterInterface

    def generate_fleet_target(self, simulation_state: 'SimulationState') -> Tuple[BasicManager, FleetStateTarget]:
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

        _, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        active_target = StateTarget(id='ACTIVE',
                                    state_set=active_set,
                                    n_vehicles=future_demand.value)

        fleet_state_target = {active_target.id: active_target}

        return self, fleet_state_target
