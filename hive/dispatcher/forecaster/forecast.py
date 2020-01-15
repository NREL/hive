from typing import NamedTuple, Dict, FrozenSet
from enum import Enum


class ForecastType(Enum):
    DEMAND = 0


class Forecast(NamedTuple):
    type: ForecastType
    value: int
    # spatial_distribution
