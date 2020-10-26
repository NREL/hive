from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.route import Route
from hive.model.sim_time import SimTime
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    sim_h3_resolution: H3Resolution
    geofence: Optional[GeoFence]

    @abstractmethod
    def route(self, origin: GeoId, destination: GeoId) -> Route:
        """
        Returns a route between two road network property links

        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: A route.
        """

    @abstractmethod
    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        """
        Returns the road network distance between two geoids

        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: the distance in kilometers.
        """

    @abstractmethod
    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        builds a location on the road network for a stationary simulation element

        :param geoid: geoid to map to network
        :return: The nearest property link if it exists.
        """

    @abstractmethod
    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance

        :param geoid: an h3 geoid
        :return: True/False
        """

    @abstractmethod
    def update(self, sim_time: SimTime) -> RoadNetwork:
        """
        requests an update to the road network state to refect the provided simulation time
        :param sim_time:
        :return:
        """
