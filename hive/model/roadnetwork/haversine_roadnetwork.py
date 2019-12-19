from __future__ import annotations

from typing import Tuple, Optional

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.typealiases import GeoId, LinkId, SimTime
from hive.util.units import unit


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
    AVG_SPEED = 40 * (unit.kilometer / unit.hour)
    sim_h3_resolution = 15

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

    def route(self, origin: PropertyLink, destination: PropertyLink) -> Route:
        start = origin.link.start
        end = destination.link.end
        link_id = self._geoids_to_link_id(start, end)

        property_link = self.get_link(link_id)

        route = (property_link,)

        return route

    def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
        link_id = self._geoids_to_link_id(geoid, geoid)
        link = Link(link_id, geoid, geoid)
        return PropertyLink(link_id, link, 0, 0, 0)

    def update(self, sim_time: SimTime) -> RoadNetwork:

        # This particular road network implementation doesn't keep track of network flow so this method does nothing.
        return self

    def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:

        if not self.link_id_within_simulation(link_id):
            return None

        start, end = self._link_id_to_geodis(link_id)
        link = Link(link_id, start, end)
        property_link = PropertyLink.build(link, self.AVG_SPEED)

        return property_link

    def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:

        return property_link

    def geoid_within_geofence(self, geoid: GeoId) -> bool:

        return True

    def link_id_within_geofence(self, link_id: LinkId) -> bool:

        start, end = self._link_id_to_geodis(link_id)
        return self.geoid_within_geofence(start) and self.geoid_within_geofence(end)

    def geoid_within_simulation(self, geoid: GeoId) -> bool:

        return True

    def link_id_within_simulation(self, link_id: LinkId) -> bool:

        start, end = self._link_id_to_geodis(link_id)
        return self.geoid_within_simulation(start) and self.geoid_within_simulation(end)
