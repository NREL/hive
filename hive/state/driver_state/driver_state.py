from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import NamedTupleMeta, Tuple, Optional

from hive.state.entity_state.entity_state import EntityState
from hive.state.simulation_state import simulation_state_ops
from hive.util import VehicleId, SimulationStateError


class DriverState(ABCMeta, NamedTupleMeta, EntityState):
    """
    superclass for all driver state instances
    """

    @property
    @abstractmethod
    def available(cls):
        pass

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    @classmethod
    def apply_new_driver_state(mcs,
                               sim: 'SimulationState',
                               vehicle_id: VehicleId,
                               new_state: DriverState
                               ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        vehicle = sim.vehicles.get(vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle_id} not found"), None
        else:
            updated_vehicle = vehicle.modify_driver_state(new_state)
            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)
