from __future__ import annotations

from typing import Tuple, Optional

from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.geofence import GeoFence
from hive.util.typealiases import GeoId, LinkId, H3Resolution
from hive.util.helpers import H3Ops
from hive.util.units import Kilometers, hours_to_seconds


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

    def _geoids_to_link_id(self, origin: GeoId, destination: GeoId) -> LinkId:
        link_id = origin + "-" + destination
        return link_id

    def _link_id_to_geodis(self, link_id: LinkId) -> Tuple[GeoId, GeoId]:
        ids = link_id.split("-")
        if len(ids) != 2:
            raise (TypeError("LinkId not in expected format of [GeoId]-[GeoId]"))
        start = ids[0]
        end = ids[1]

        return start, end

    def route(self, origin: GeoId, destination: GeoId) -> Route:
        link_id = self._geoids_to_link_id(origin, destination)
        link_dist_km = self.distance_by_geoid_km(origin, destination)
        link_travel_time_seconds = hours_to_seconds(link_dist_km / self._AVG_SPEED_KMPH)
        link = Link(
            link_id=link_id,
            start=origin,
            end=destination,
            distance_km=link_dist_km,
            speed_kmph=self._AVG_SPEED_KMPH,
            travel_time_seconds=link_travel_time_seconds,
        )

        route = (link,)

        return route

    def distance_km(self, origin: Link, destination: Link) -> Kilometers:
        return H3Ops.great_circle_distance(origin.start, destination.end)

    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        return H3Ops.great_circle_distance(origin, destination)

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        link_id = self._geoids_to_link_id(geoid, geoid)
        return Link(
            link_id=link_id,
            start=geoid,
            end=geoid,
            distance_km=0,
            speed_kmph=0,
            travel_time_seconds=0,
        )

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        if not self.geofence:
            raise RuntimeError("Geofence not specified.")
        else:
            return self.geofence.contains(geoid)
