from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from typing import Optional

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.route import Route
from hive.util.helpers import H3Ops
from hive.util.typealiases import GeoId, LinkId, Km, Time


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    sim_h3_resolution: int

    @functools.cached_property
    def neighboring_hex_distance(self) -> Km:
        """
        gives the distance between neighboring hexes at this simulation resolution
        :return: neighboring hex centroid distance at this resolution
        """
        return H3Ops.distance_between_neighboring_hex_centroids(self.sim_h3_resolution)

    @abstractmethod
    def route(self, origin: Link, destination: Link) -> Route:
        pass

    @abstractmethod
    def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
        """
        builds a location on the road network for a stationary simulation element
        :param geoid:
        :return:
        """
        pass

    @abstractmethod
    def update(self, sim_time: Time) -> RoadNetwork:
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the current simulation time
        :return: does not return
        """
        pass

    @abstractmethod
    def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
        """
        gets the link associated with the LinkId, or, if invalid, returns None
        :param link_id: a link id
        :return: a Link, or None if LinkId does not exist
        """
        pass

    @abstractmethod
    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param geoid: an h3 geoid
        :return: True/False
        """
        pass

    @abstractmethod
    def link_id_within_geofence(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        pass

    @abstractmethod
    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param geoid: an h3 geoid
        :return: True/False
        """
        pass

    @abstractmethod
    def link_id_within_simulation(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        pass
