from __future__ import annotations

from abc import abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta
from hive.dispatcher.forecaster.forecast import Forecast


class ForecasterInterface(metaclass=ABCNamedTupleMeta):
    """
    A class that computes an optimal fleet state.
    """

    @abstractmethod
    def generate_forecast(self, simulation_state: SimulationState) -> Tuple[ForecasterInterface, Forecast]:
        """
        Generate forecast of some future state.

        :param simulation_state: The current simulation state
        :return: the update Forecaster along with the forecast
        """
