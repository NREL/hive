from typing import NamedTuple, Tuple, Optional

from hive.reporting.driver_event_ops import driver_schedule_event, ScheduleEventType
from hive.dispatcher.instruction.instructions import DispatchBaseInstruction
from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
from hive.state.simulation_state.simulation_state_ops import add_instruction

from hive.util import SimulationStateError
from hive.util.typealiases import ScheduleId

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

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
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

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        :param sim:
        :param env:
        :return:
        """
        return_home = DispatchBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id)
        return add_instruction(sim, self.attributes.vehicle_id, return_home)

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
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