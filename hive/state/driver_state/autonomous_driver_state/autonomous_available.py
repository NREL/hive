from typing import NamedTuple, Tuple, Optional

from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
from hive.state.driver_state.driver_state import DriverState


class AutonomousAvailable(NamedTuple, DriverState):
    """
    an autonomous driver that is available to work
    """
    driver_attributes: AutonomousDriverAttributes

    @property
    def available(cls):
        return True

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        # there is no other state for an autonomous driver, so, this is a noop
        return sim
