from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union, TYPE_CHECKING

import networkx as nx

from nrel.hive.model.roadnetwork.geofence import GeoFence
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.roadnetwork.link import Link
from nrel.hive.model.roadnetwork.link_id import extract_node_ids
from nrel.hive.model.roadnetwork.osm.osm_builders import osm_graph_from_polygon
from nrel.hive.model.roadnetwork.osm.osm_road_network_link_helper import OSMRoadNetworkLinkHelper
from nrel.hive.model.roadnetwork.osm.osm_roadnetwork_ops import (
    route_from_nx_path,
    resolve_route_src_dst_positions,
)
from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
from nrel.hive.model.roadnetwork.route import (
    Route,
    route_distance_km,
    empty_route,
)
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util import LinkId
from nrel.hive.util.typealiases import GeoId, H3Resolution
from nrel.hive.util.units import Kmph, Kilometers
from nrel.hive.model.roadnetwork.link_id import extract_node_ids

log = logging.getLogger(__name__)


class OSMRoadNetwork(RoadNetwork):
    """
    Implements an open street maps road network utilizing the osmnx and networkx libraries

    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        sim_h3_resolution: H3Resolution = 15,
        default_speed_kmph: Kmph = 40.0,
    ):
        self.sim_h3_resolution = sim_h3_resolution

        # validate network

        #   road network must be strongly connected
        if not nx.is_strongly_connected(graph):
            raise RuntimeError("Only strongly connected graphs are allowed.")

        #   node ids must be either an integer or a tuple of integers
        def _valid_node_id(nid: Union[int, tuple]) -> bool:
            if isinstance(nid, int):
                return True
            elif isinstance(nid, tuple):
                return all([isinstance(n, int) for n in nid])
            else:
                return False

        if not all(map(_valid_node_id, graph.nodes())):
            raise TypeError("all node ids must be either an integer or a tuple of integers")

        #   check to make sure the graph has the right information on the links
        missing_length = 0
        missing_speed = 0
        for _, _, d in graph.edges(data=True):
            if "length" not in d:
                missing_length += 1
            if "speed_kmph" not in d:
                missing_speed += 1
        if missing_length > 0:
            raise Exception(
                f"found {missing_length} links in the road network that don't have length information"
            )
        elif missing_speed > 0:
            log.warning(
                f"found {missing_speed} links in the road network that don't have speed information.\n"
                f"hive will automatically set these to {default_speed_kmph} kmph."
            )

        # build tables on the network edges for spatial lookup and LinkId lookup
        link_helper_error, link_helper = OSMRoadNetworkLinkHelper.build(
            graph, sim_h3_resolution, default_speed_kmph
        )
        if link_helper_error:
            raise link_helper_error
        elif link_helper is None:
            raise Exception("Was not able to build link helper")
        else:
            # finish constructing OSMRoadNetwork instance
            self.graph = graph
            self.link_helper = link_helper

    @classmethod
    def from_polygon(
        cls,
        polygon,
        sim_h3_resolution: H3Resolution = 15,
        default_speed_kmph: Kmph = 40.0,
    ) -> OSMRoadNetwork:
        """
        Build an OSMRoadNetwork from a shapely polygon

        :param polygon: The polygon to build the road network from
        :param sim_h3_resolution: The h3 resolution of the simulation
        :param default_speed_kmph: The network will fill in missing speed values with this
        """
        graph = osm_graph_from_polygon(polygon)
        return OSMRoadNetwork(graph, sim_h3_resolution, default_speed_kmph)

    @classmethod
    def from_file(
        cls,
        road_network_file: Union[Path, str],
        sim_h3_resolution: H3Resolution = 15,
        default_speed_kmph: Kmph = 40.0,
    ) -> OSMRoadNetwork:
        """
        Build an OSMRoadNetwork from file
        """
        road_network_path = Path(road_network_file)
        # read in the network file
        if road_network_path.suffix == ".json":
            with road_network_path.open("r") as f:
                graph = nx.node_link_graph(json.load(f))
            return OSMRoadNetwork(graph, sim_h3_resolution, default_speed_kmph)
        else:
            raise TypeError(
                f"road network file of type {road_network_path.suffix} not supported by OSMRoadNetwork."
            )

    def to_file(self, file: Union[str, Path]):
        path = Path(file)

        with path.open("w") as f:
            json.dump(nx.node_link_data(self.graph), f)

    def route(self, origin: EntityPosition, destination: EntityPosition) -> Route:
        """
        Returns a route containing road network links between the origin and destination geoids.

        :param origin: the origin Link
        :param destination: the destination Link
        :return: a route between the origin and destination on the OSM road network
        """
        if origin == destination:
            return empty_route()

        # start path search from the end of the origin link, terminate search at the start of the destination link
        extract_src_err, src_nodes = extract_node_ids(origin.link_id)
        extract_dst_err, dst_nodes = extract_node_ids(destination.link_id)
        if extract_src_err:
            log.error(extract_src_err)
            return empty_route()
        elif extract_dst_err:
            log.error(extract_dst_err)
            return empty_route()
        elif src_nodes is None:
            return empty_route()
        elif dst_nodes is None:
            return empty_route()
        else:
            _, origin_node_id = src_nodes
            destination_node_id, _ = dst_nodes

            # node-oriented shortest path from the end of the origin link to the beginning of the destination link
            nx_path = nx.shortest_path(self.graph, origin_node_id, destination_node_id)
            link_path_error, inner_link_path = route_from_nx_path(nx_path, self.link_helper.links)

            if link_path_error:
                log.error(f"unable to build route from {origin} to {destination}")
                log.error(link_path_error)
                log.error(
                    f"origin node {origin_node_id}, destination node {destination_node_id}, shortest path node list result: {nx_path}"
                )
                return empty_route()
            elif inner_link_path is None:
                return empty_route()
            else:
                # modify the start and end GeoIds based on the positions in the src/dst links
                resolved_route = resolve_route_src_dst_positions(
                    inner_link_path, origin, destination, self
                )
                if not resolved_route:
                    log.error(
                        f"unable to resolve the route from/to/via:\n {origin}\n{destination}\n{inner_link_path}"
                    )
                    return empty_route()
                else:
                    return resolved_route

    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        """
        Returns the road network distance between the origin and destination

        :param origin: the geoid of the origin
        :param destination: the geoid of the destination
        :return: the road network distance in kilometers
        """
        o = self.position_from_geoid(origin)
        d = self.position_from_geoid(destination)
        if not o or not d:
            log.error(
                f"failed finding nearest links to distance query between GeoIds {origin}, {destination}"
            )
            return 0.0
        else:
            distance = route_distance_km(self.route(o, d))
            return distance

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        Returns the closest link to a geoid.

        :param geoid: the geoid to snap to the road newtork
        :return: the link on the road network that is closest to the geoid
        """
        error, link = self.link_helper.link_by_geoid(geoid)
        if error:
            log.warning(f"unable to find nearest link to geoid {geoid}")
            log.error(error)
            return None
        else:
            return link

    def link_from_link_id(self, link_id: LinkId) -> Optional[Link]:
        """
        look up the provided LinkId in the LinkHelper table
        :param link_id: the LinkId to look up
        :return: the Link if it exists, otherwise None
        """
        link = self.link_helper.links.get(link_id)
        return link

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        Determines if a specific geoid is contained within the road network geofence.


        :param geoid: the geoid to test
        :return: True/False
        """
        return True
        # TODO: the geofence is slated to be modified and so we're bypassing this check in the meantime.
        #  we'll need to add it back once we update the geofence implementation.

    def update(self, sim_time: SimTime) -> RoadNetwork:
        raise NotImplementedError("updates are not implemented")
