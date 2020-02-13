from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.geofence import GeoFence
from hive.util.typealiases import GeoId, LinkId, H3Resolution


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    sim_h3_resolution: H3Resolution
    geofence: GeoFence

    @abstractmethod
    def route(self, origin: PropertyLink, destination: PropertyLink) -> Route:
        """
        Returns a route between two road network property links

        :param origin: PropertyLink of the origin
        :param destination: PropertyLink of the destination
        :return: A route.
        """

    @abstractmethod
    def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
        """
        builds a location on the road network for a stationary simulation element

        :param geoid: geoid to map to network
        :return: The nearest property link if it exists.
        """


    @abstractmethod
    def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
        """
        gets the link associated with the LinkId, or, if invalid, returns None

        :param link_id: a link id
        :return: a Link, or None if LinkId does not exist
        """

    @abstractmethod
    def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
        """
        gets the current properties for a given property link, or, if invalid, returns None

        :param property_link: a property link
        :return: a Property Link, or None if LinkId does not exist
        """

    @abstractmethod
    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance

        :param geoid: an h3 geoid
        :return: True/False
        """

