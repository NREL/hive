from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import NamedTupleMeta, Tuple, Optional, TYPE_CHECKING

from hive.util import SimulationStateError
from hive.state.simulation_state import simulation_state_ops
from hive.state.entity_state.entity_state import EntityState

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.util.typealiases import ScheduleId, BaseId, VehicleId
    from hive.dispatcher.instruction.instruction import Instruction


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
    def generate_instruction(
            self,
            sim: SimulationState,
            env: Environment,
            previous_instructions: Optional[Tuple[Instruction, ...]],
    ) -> Optional[Instruction]:
        """
        allows the driver state to issue an optional instruction for the vehicle considering all the
        previous instructions generated by the dispatcher


        :param sim:
        :param env:
        :param previous_instructions:
        :return:
        """
        return None

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        """
        there are no operations associated with entering a DriverState

        :param sim: the simulation state
        :param env: the simulation environment
        :return: always the unmodified simulation state
        """
        return None, sim

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        """
        there are no operations associated with exiting a DriverState

        :param sim: the simulation state
        :param env: the simulation environment
        :return: always the unmodified simulation state
        """
        return None, sim

    @classmethod
    def apply_new_driver_state(mcs,
                               sim: SimulationState,
                               vehicle_id: VehicleId,
                               new_state: DriverState
                               ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
    def build(mcs,
              vehicle_id: VehicleId,
              schedule_id: Optional[ScheduleId],
              base_id: Optional[BaseId],
              ) -> DriverState:
        """
        constructs a new DriverState based on the provided arguments

        :param vehicle_id: the Vehicle associated with this DriverState
        :param schedule_id: if provided, sets the DriverState as a HumanUnavailable driver
        :param base_id: used for HumanAvailable and HumanUnavailable
        :return: the driver state instance created
        """
        from hive.state.driver_state.autonomous_driver_state.autonomous_available import AutonomousAvailable
        from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
        from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
        from hive.state.driver_state.human_driver_state.human_driver_state import HumanUnavailable
        if not schedule_id:
            driver_state = AutonomousAvailable(AutonomousDriverAttributes(vehicle_id))
            return driver_state
        else:
            if not base_id:
                raise Exception("cannot build a vehicle with schedule but not a home base id")
            driver_state = HumanUnavailable(HumanDriverAttributes(vehicle_id, schedule_id, base_id))
            return driver_state
