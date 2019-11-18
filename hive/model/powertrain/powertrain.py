from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from hive.roadnetwork.link import Link
from hive.roadnetwork.route import Route
from hive.util.typealiases import KwH, PowertrainId


class PowertrainType(Enum):
    BEV = 0
    PHEV = 1
    GAS = 2
    DIESEL = 3
    HYDROGEN = 4


class Powertrain(ABC):
    """
    a powertrain has a behavior where it consumes routes or route steps
    and returns an energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowertrainId:
        pass

    @abstractmethod
    def route_fuel_cost(self, route: Route) -> KwH:
        pass

    @abstractmethod
    def route_step_fuel_cost(self, route_step: Link) -> KwH:
        pass
