from typing import NamedTuple, Tuple, Optional

from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes

# these two classes (HumanAvailable, HumanUnavailable) are in the same file in order to avoid circular references
from hive.util.typealiases import ScheduleId


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
        if not schedule_function or schedule_function(sim, self.attributes.vehicle_id):
            # stay available
            return None, sim
        else:
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

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is unavailable to work. if not, transition to an available state.

        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        if not schedule_function or schedule_function(sim, self.attributes.vehicle_id):
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