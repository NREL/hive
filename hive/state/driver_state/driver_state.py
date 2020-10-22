from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import NamedTupleMeta, Tuple, Optional

from hive.state.entity_state.entity_state import EntityState
from hive.state.simulation_state import simulation_state_ops
from hive.util import VehicleId, SimulationStateError
from hive.util.typealiases import ScheduleId


class DriverState(ABCMeta, NamedTupleMeta, EntityState):
    """
    superclass for all driver state instances
    """

    @property
    @abstractmethod
    def schedule_id(cls) -> Optional[ScheduleId]:
        pass

    @property
    @abstractmethod
    def available(cls):
        pass

    @abstractmethod
    def update(self,
               sim: 'SimulationState',
               env: 'Environment',
               ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        
        :param sim: 
        :param env: 
        :param **kwargs: optional keyword arguments
        :return: 
        """
        pass

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        there are no operations associated with entering a DriverState
        :param sim: the simulation state
        :param env: the simulation environment
        :return: always the unmodified simulation state
        """
        return None, sim

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        there are no operations associated with exiting a DriverState
        :param sim: the simulation state
        :param env: the simulation environment
        :return: always the unmodified simulation state
        """
        return None, sim

    @classmethod
    def apply_new_driver_state(mcs,
                               sim: 'SimulationState',
                               vehicle_id: VehicleId,
                               new_state: DriverState
                               ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        helper for updating a Vehicle with a new DriverState
        :param sim: the simulation state
        :param vehicle_id: the id of the vehicle to update
        :param new_state: the state to apply to the vehicle
        :return: the updated sim, or, an error
        """
        vehicle = sim.vehicles.get(vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle_id} not found"), None
        else:
            updated_vehicle = vehicle.modify_driver_state(new_state)
            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)

    @classmethod
    def build(mcs, vehicle_id: VehicleId, schedule_id: Optional[ScheduleId]) -> DriverState:
        """
        constructs a new DriverState based on the provided arguments
        :param vehicle_id: the Vehicle associated with this DriverState
        :param schedule_id: if provided, sets the DriverState as a HumanUnavailable driver
        :return: the driver state instance created
        """
        from hive.state.driver_state.autonomous_driver_state.autonomous_available import AutonomousAvailable
        from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
        from hive.state.driver_state.human_driver_state.human_driver_state import HumanUnavailable
        if not schedule_id:
            driver_state = AutonomousAvailable()
            return driver_state
        else:
            driver_state = HumanUnavailable(HumanDriverAttributes(vehicle_id, schedule_id))
            return driver_state
