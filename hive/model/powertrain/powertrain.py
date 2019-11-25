from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.util.typealiases import KwH, PowertrainId


class Powertrain(ABC):
    """
    a powertrain has a behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowertrainId:
        pass

    @abstractmethod
    def route_energy_cost(self, route: Tuple[PropertyLink, ...], road_network: RoadNetwork) -> KwH:
        """
        (estimated) energy cost to traverse this route
        :param route: a route
        :param road_network: the road network
        :return: energy cost
        """
        pass

    @abstractmethod
    def segment_energy_cost(self, segment: RouteSegment, road_network: RoadNetwork) -> KwH:
        """
        gives the energy cost to traverse this segment. starts at "percent complete" of
        the first link, and goes until "percent complete" of the last link
        :param segment: a segment
        :param road_network: the road network
        :return: energy cost
        """
        pass

    @abstractmethod
    def start_link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        """
        gets the link cost for traversal, starting from "percent complete" of the link
        :param link: a link
        :param road_network: the road network
        :return: energy cost
        """
        pass

    @abstractmethod
    def end_link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        """
        gets the link cost for traversal, ending at "percent complete" of the link
        :param link: a link
        :param road_network: the road network
        :return: energy cost
        """
        pass

    @abstractmethod
    def link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        """
        gets the link cost for traversal, ignoring "percent complete" of the link
        :param link: a link
        :param road_network: the road network
        :return: energy cost
        """
        pass
