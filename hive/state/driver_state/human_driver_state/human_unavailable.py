from typing import NamedTuple, Tuple, Optional

from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_available import HumanAvailable
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes


class HumanUnavailable(NamedTuple, DriverState):
    """
    a human driver that is available to work
    """
    human_driver_attributes: HumanDriverAttributes

    @property
    def available(cls):
        return False

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is unavailable to work

        :param sim:
        :param env:
        :return:
        """
        schedule_function = env.schedules.get(self.human_driver_attributes.schedule_id)
        if not schedule_function or not schedule_function(sim.sim_time):
            # transition to available, because of one of these reasons:
            #   being unavailable but not having a schedule is invalid.
            #   the schedule function returns true, so, we should be activated
            next_state = HumanAvailable(self.human_driver_attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.human_driver_attributes.vehicle_id,
                                                        next_state)
            return result
        else:
            # stay unavailable
            return None, sim
