from __future__ import annotations

from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.manager.fleet_targets.active_fleet_target import ActiveFleetTarget
from hive.dispatcher.manager.manager_interface import ManagerInterface

if TYPE_CHECKING:
    from hive.dispatcher.manager.fleet_targets.fleet_target_interface import FleetTarget
    from hive.util.typealiases import Report


class BasicManager(NamedTuple, ManagerInterface):
    """
    A class that computes an optimal fleet state.
    """
    demand_forecaster: ForecasterInterface

    def generate_fleet_targets(
            self,
            simulation_state: 'SimulationState',

    ) -> Tuple[BasicManager, Tuple[FleetTarget, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets to be consumed by the dispatcher.

        :param simulation_state: The current simulation state
        :return: the update Manager along with the fleet target
        """
        # TODO: add a vehicle state id to vehicle states to compare
        active_set = frozenset({
            "Idle",
            "ServicingTrip",
            "DispatchTrip",
            "DispatchStation",
            "ChargingStation",
            "Repositioning",
        })

        updated_forecaster, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        active_target = ActiveFleetTarget(
            n_active_vehicles=future_demand.value,
            active_set=active_set,
        )

        next_manager = self._replace(demand_forecaster=updated_forecaster)

        return next_manager, (active_target, ), ()
