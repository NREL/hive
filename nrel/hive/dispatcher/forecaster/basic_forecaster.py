from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, TYPE_CHECKING

from nrel.hive.dispatcher.forecaster.forecast import Forecast, ForecastType
from nrel.hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util.iterators import DictReaderStepper

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState


@dataclass(frozen=True)
class BasicForecaster(ForecasterInterface):
    """
    A forecaster that generates a prediction based on the current demand.
    """

    reader: DictReaderStepper

    @classmethod
    def build(cls, demand_forecast_file: str) -> BasicForecaster:
        """
        loads a forecaster from a file

        :param demand_forecast_file: the file source
        :return: a BasicForecaster
        :raises: an exception if there were file loading issues
        """
        if not Path(demand_forecast_file).is_file():
            raise IOError(f"{demand_forecast_file} is not a valid path to a request file")

        error, reader = DictReaderStepper.build(
            demand_forecast_file, "sim_time", parser=SimTime.build
        )
        if error:
            raise error
        else:
            if reader is None:
                raise Exception("No reader supplied by the DictReaderStepper")

            return BasicForecaster(reader)

    def generate_forecast(
        self, simulation_state: SimulationState
    ) -> Tuple[BasicForecaster, Forecast]:
        """
        Generate fleet targets to be consumed by the dispatcher.

        :param simulation_state: The current simulation state
        :return: the update Manager along with the fleet target
        """
        current_demand = len(simulation_state.requests)

        current_sim_time = simulation_state.sim_time

        # grab all requests in the next 30 minutes
        def stop_condition(value: int) -> bool:
            return value < current_sim_time + (30 * 60)

        demand_result = tuple(self.reader.read_until_stop_condition(stop_condition))
        future_demand = sum([int(n["requests"]) for n in demand_result])

        demand_forecast = Forecast(type=ForecastType.DEMAND, value=current_demand + future_demand)

        return self, demand_forecast
