from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState

from nrel.hive.dispatcher.forecaster.forecast import Forecast


class ForecasterInterface(ABC):
    """
    A class that computes an optimal fleet state.
    """

    @abstractmethod
    def generate_forecast(
        self, simulation_state: SimulationState
    ) -> Tuple[ForecasterInterface, Forecast]:
        """
        Generate forecast of some future state.

        :param simulation_state: The current simulation state
        :return: the update Forecaster along with the forecast
        """
