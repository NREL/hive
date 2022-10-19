from enum import Enum
from typing import NamedTuple


class ForecastType(Enum):
    DEMAND = 0


class Forecast(NamedTuple):
    type: ForecastType
    value: int
    # spatial_distribution
