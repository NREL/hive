from typing import NamedTuple, Tuple, Optional

import immutables

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import DispatchBaseInstruction
from hive.reporting.driver_event_ops import driver_schedule_event, ScheduleEventType
from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.dispatch_base import DispatchBase
from hive.util import SimulationStateError
from hive.util.typealiases import ScheduleId, VehicleId


# these two classes (HumanAvailable, HumanUnavailable) are in the same file in order to avoid circular references


class HumanAvailable(NamedTuple, DriverState):
    """
    a human driver that is available to work as the current simulation state is consistent with
    the driver's schedule function
    """
    attributes: HumanDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return cls.attributes.schedule_id

    @property
    def available(cls):
        return True

    def generate_instruction(
            self,
            sim: 'SimulationState',
            env: 'Environment',
            previous_instructions: Optional[Tuple[Instruction, ...]],
    ) -> Optional[Instruction]:
        return None

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is available to work. if unavailable, transition to an unavailable state.

        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if not schedule_function or schedule_function(sim, self.attributes.vehicle_id):
            # stay available
            return None, sim
        elif not vehicle:
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found")
            return error, None
        else:
            # log transition
            report = driver_schedule_event(sim, env, vehicle, ScheduleEventType.OFF)
            env.reporter.file_report(report)

            # transition to unavailable
            next_state = HumanUnavailable(self.attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.attributes.vehicle_id,
                                                        next_state)
            return result


class HumanUnavailable(NamedTuple, DriverState):
    """
    a human driver that is available to work
    """
    attributes: HumanDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return cls.attributes.schedule_id

    @property
    def available(cls):
        return False

    def generate_instruction(
            self,
            sim: 'SimulationState',
            env: 'Environment',
            previous_instructions: Optional[Tuple[Instruction, ...]],
    ) -> Optional[Instruction]:
        """
        while in this state, the driver checks the vehicle location; if the vehicle is not at the home base,
        a new instruction is generated to send the vehicle home.

        :param sim:
        :param env:
        :param previous_instructions:
        :return:
        """

        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)
        my_base = sim.bases.get(self.attributes.home_base_id)

        if not my_base.geoid == my_vehicle.geoid and not isinstance(my_vehicle.vehicle_state, DispatchBase):
            i = DispatchBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id)
        else:
            i = None

        return i

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is unavailable to work. if not, transition to an available state.

        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if not vehicle:
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found")
            return error, None
        elif schedule_function and schedule_function(sim, self.attributes.vehicle_id):
            # log transition
            report = driver_schedule_event(sim, env, vehicle, ScheduleEventType.ON)
            env.reporter.file_report(report)

            # transition to available, because of one of these reasons:
            #   being unavailable but not having a schedule is invalid.
            #   the schedule function returns true, so, we should be activated
            next_state = HumanAvailable(self.attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.attributes.vehicle_id,
                                                        next_state)
            return result
        else:
            # stay unavailable
            return None, sim
