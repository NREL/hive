from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state import SimulationState

from hive.dispatcher.manager.fleet_target import FleetStateTarget
from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta


class ManagerInterface(metaclass=ABCNamedTupleMeta):
    """
    A class that computes an optimal fleet state.
    """

    @abstractmethod
    def generate_fleet_target(self, simulation_state: SimulationState) -> Tuple[Manager, FleetStateTarget]:
        """
        Generate fleet targets to be consumed by the dispatcher.

        :param simulation_state: The current simulation state
        :return: the update Manager along with the fleet target
        """
        pass
