from __future__ import annotations

from typing import Tuple, NamedTuple

from hive.state.simulation_state import SimulationState
from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.forecaster.forecast import Forecast, ForecastType


class BasicForecaster(NamedTuple, ForecasterInterface):
    """
    A forecaster that generates a prediction based on the current demand.
    """

    def generate_forecast(self, simulation_state: SimulationState) -> Tuple[BasicForecaster, Forecast]:
        """
        Generate fleet targets to be consumed by the dispatcher.

        :param simulation_state: The current simulation state
        :return: the update Manager along with the fleet target
        """
        current_demand = len(simulation_state.requests)

        demand_forecast = Forecast(type=ForecastType.DEMAND, value=current_demand + 10)

        return self, demand_forecast
