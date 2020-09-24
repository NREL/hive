from abc import ABCMeta, abstractmethod
from typing import NamedTupleMeta, Tuple, Optional

from hive.state.entity_state.entity_state import EntityState


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

# a driver state allows us to add a separate set of states which can influence the
# behavior of vehicles due to effects which are not fleet-related, but still
# are accounted for on the agent-level.

# a driver can be human or automated.

# when the simulation attempts any fleet instructions, the set of vehicles
# is to be filtered on the condition of "availability". an unavailable agent
# is for example a human that is off-shift.

