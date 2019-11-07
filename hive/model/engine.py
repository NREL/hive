from abc import ABC, abstractmethod
from hive.roadnetwork.routestep import RouteStep
from hive.roadnetwork.route import Route
from hive.util.typealiases import KwH


class Engine(ABC):
    """
    an engine has a behavior where it consumes routes or route steps
    and returns an energy consumption in KwH
    """

    @abstractmethod
    def route_fuel_cost(self, route: Route) -> KwH:
        pass

    @abstractmethod
    def route_step_fuel_cost(self, route_step: RouteStep) -> KwH:
        pass
