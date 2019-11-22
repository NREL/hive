from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from typing import Tuple, Optional

from h3 import h3

from hive.roadnetwork.link import PropertyLink, Link
from hive.util.typealiases import GeoId, LinkId, Km


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    sim_h3_resolution: int

    @functools.cached_property
    def average_hex_distance(self) -> Km:
        """
        sides to a hex are a fixed length at any resolution. moving
        horizontally between two equally-sized hexes is equal to the distance
        of 2 sides. this sets an upper-bound on hex distances, and can be used
        for distance estimates
        :return: average hex distance at this resolution
        """
        avg_edge_length = h3.edge_length(self.sim_h3_resolution)
        return avg_edge_length * 2

    @abstractmethod
    def route_by_geoid(self, origin: GeoId, destination: GeoId) -> Tuple[Link, ...]:
        pass

    # @abstractmethod
    # def route_by_position(self, origin: Position, destination: Position) -> Tuple[Link, ...]:
    #     pass

    @abstractmethod
    def update(self, sim_time: int) -> RoadNetwork:
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the sim time to update the model to
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

    # @abstractmethod
    # def advance_position(self, start_position: Position, route: Route) -> Tuple[Position, ExperiencedRouteSteps]:
    #     """
    #
    #     :param start_position:
    #     :param route:
    #     :return:
    #     """
    #     pass
    #
    # @abstractmethod
    # def position_to_geoid(self, postition: Position, resolution: int) -> GeoId:
    #     """
    #     does the work to determine the coordinate of this position on the road network
    #     :param link_id: a position on the road network
    #     :param resolution: h3 resolution
    #     :return: an h3 geoid at this position
    #     """
    #     pass
    #
    # @abstractmethod
    # def geoid_within_geofence(self, geoid: GeoId) -> bool:
    #     """
    #     confirms that the coordinate exists within the bounding polygon of this road network instance
    #     :param geoid: an h3 geoid
    #     :return: True/False
    #     """
    #     pass
    #
    # @abstractmethod
    # def link_id_within_geofence(self, link_id: LinkId) -> bool:
    #     """
    #     confirms that the coordinate exists within the bounding polygon of this road network instance
    #     :param link_id: a position on the road network across the entire simulation
    #     :return: True/False
    #     """
    #     pass
    #
    # @abstractmethod
    # def geoid_within_simulation(self, geoid: GeoId) -> bool:
    #     """
    #     confirms that the coordinate exists within the bounding polygon the entire simulation,
    #     which may include many (distributed) RoadNetwork instances
    #     :param geoid: an h3 geoid
    #     :return: True/False
    #     """
    #     pass
    #
    # @abstractmethod
    # def link_id_within_simulation(self, link_id: LinkId) -> bool:
    #     """
    #     confirms that the coordinate exists within the bounding polygon the entire simulation,
    #     which may include many (distributed) RoadNetwork instances
    #     :param link_id: a position on the road network across the entire simulation
    #     :return: True/False
    #     """
    #     pass
    #
