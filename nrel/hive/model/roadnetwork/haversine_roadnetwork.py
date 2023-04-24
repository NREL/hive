from __future__ import annotations

from typing import Optional

import nrel.hive.model.roadnetwork.haversine_link_id_ops as h_ops
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.roadnetwork.geofence import GeoFence
from nrel.hive.model.roadnetwork.link import Link
from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal
from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
from nrel.hive.model.roadnetwork.route import Route, empty_route
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util.h3_ops import H3Ops
from nrel.hive.util.typealiases import GeoId, LinkId, H3Resolution
from nrel.hive.util.units import Kilometers


class HaversineRoadNetwork(RoadNetwork):
    """
    Implements a simple haversine road network where a unique node exists for each unique GeoId in the simulation.
    This assumes a fully connected graph between each node in which the shortest path is the link that connects any
    two nodes. LinkId is specified as a concatenation of the GeoId of its endpoints in which the order is given by
    origin and destination respectively.


    :param AVG_SPEED: the average speed over the network
    :type AVG_SPEED: :py:obj: kilometer/hour

    :param sim_h3_resolution: the h3 simulation level resolution. default 15
    :type sim_h3_resolution: :py:obj: int

    """

    # TODO: Replace speed with more accurate/dynamic estimate.
    _AVG_SPEED_KMPH = 40  # kilometer / hour

    def __init__(
        self,
        geofence: Optional[GeoFence] = None,
        sim_h3_resolution: H3Resolution = 15,
    ):
        self.sim_h3_resolution = sim_h3_resolution
        self.geofence = geofence

    def route(self, origin: EntityPosition, destination: EntityPosition) -> Route:
        if origin == destination:
            return empty_route()

        link_id = h_ops.geoids_to_link_id(origin.geoid, destination.geoid)
        link_dist_km = self.distance_by_geoid_km(origin.geoid, destination.geoid)
        link = LinkTraversal(
            link_id=link_id,
            start=origin.geoid,
            end=destination.geoid,
            distance_km=link_dist_km,
            speed_kmph=self._AVG_SPEED_KMPH,
        )

        route = (link,)

        return route

    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        return H3Ops.great_circle_distance(origin, destination)

    def link_from_link_id(self, link_id: LinkId) -> Optional[Link]:
        src, dst = h_ops.link_id_to_geodis(link_id)
        dist = self.distance_by_geoid_km(src, dst)
        link = Link(link_id, src, dst, dist, self._AVG_SPEED_KMPH)
        return link

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        link_id = h_ops.geoids_to_link_id(geoid, geoid)
        return Link(
            link_id=link_id,
            start=geoid,
            end=geoid,
            distance_km=0,
            speed_kmph=0,
        )

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        return True
        # TODO: the geofence is slated to be modified and so we're bypassing this check in the meantime.
        #  we'll need to add it back once we update the geofence implementation.

        # if not self.geofence:
        #     raise RuntimeError("Geofence not specified.")
        # else:
        #     return self.geofence.contains(geoid)

    def update(self, sim_time: SimTime) -> RoadNetwork:
        raise NotImplementedError("updates are not implemented")
