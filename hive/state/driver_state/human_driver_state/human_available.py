from typing import NamedTuple, Tuple, Optional

from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
from hive.state.driver_state.human_driver_state.human_unavailable import HumanUnavailable
from hive.util import SimulationStateError


class HumanAvailable(NamedTuple, DriverState):
    """
    a human driver that is available to work
    """
    human_driver_attributes: HumanDriverAttributes

    @property
    def available(cls):
        return True

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is available to work

        :param sim:
        :param env:
        :return:
        """
        schedule_function = env.schedules.get(self.human_driver_attributes.schedule_id)
        if not schedule_function or schedule_function(sim.sim_time):
            # stay available
            return None, sim
        else:
            # transition to unavailable
            next_state = HumanUnavailable(self.human_driver_attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.human_driver_attributes.vehicle_id,
                                                        next_state)
            return result
