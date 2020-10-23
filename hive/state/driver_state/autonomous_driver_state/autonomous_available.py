from typing import NamedTuple, Tuple, Optional

from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
from hive.state.driver_state.driver_state import DriverState
from hive.dispatcher.instruction.instruction import Instruction
from hive.util.typealiases import ScheduleId


class AutonomousAvailable(NamedTuple, DriverState):
    """
    an autonomous driver that is available to work
    """
    attributes: AutonomousDriverAttributes = AutonomousDriverAttributes()

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return None

    @property
    def available(cls):
        return True

    def generate_instruction(
            self,
            sim: 'SimulationState',
            env: 'Environment',
            previous_instructions,
    ) -> Optional[Instruction]:
        return None

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        # there is no other state for an autonomous driver, so, this is a noop
        return None, sim
