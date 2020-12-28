from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

import h3
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

from hive.external.miniosmnx.core import graph_from_file
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route, route_distance_km
from hive.model.sim_time import SimTime
from hive.util.h3_ops import H3Ops
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers, Kmph, M_TO_KM

log = logging.getLogger(__name__)


class OSMRoadNetwork(RoadNetwork):
    """
    Implements an open street maps road network utilizing the osmnx and networkx libraries
    """

    def __init__(
            self,
            road_network_file: Path,
            geofence: Optional[GeoFence] = None,
            sim_h3_resolution: H3Resolution = 15,
            default_speed_kmph: Kmph = 40.0,
    ):
        self.sim_h3_resolution = sim_h3_resolution
        self.geofence = geofence

        self.default_speed_kmph = default_speed_kmph

        if road_network_file.suffix == ".xml":
            log.warning(".xml files have been deprecated in hive. please switch to using .json formats")
            G = graph_from_file(str(road_network_file))
        elif road_network_file.suffix == ".json":
            with road_network_file.open('r') as f:
                G = nx.node_link_graph(json.load(f))
        else:
            raise TypeError(f"road network file of type {road_network_file.suffix} not supported by OSMRoadNetwork.")

        if not nx.is_strongly_connected(G):
            raise RuntimeError("Only strongly connected graphs are allowed.")

        #  label each node with an h3 geoid so we can building links from the graph
        geoid_map = {}
        geoid_to_node_id = {}
        for nid in G.nodes():
            node = G.nodes[nid]
            try:
                geoid = h3.geo_to_h3(node['y'], node['x'], resolution=self.sim_h3_resolution)
            except KeyError:
                try:
                    geoid = h3.geo_to_h3(node['lat'], node['lon'], resolution=self.sim_h3_resolution)
                except KeyError:
                    raise Exception("node attributes must have either (y, x) or (lat, lon) information")

            geoid_map[nid] = {'geoid': geoid}
            geoid_to_node_id[geoid] = nid

        nx.set_node_attributes(G, geoid_map)

        # check to make sure the graph has the right information on the links
        missing_length = 0
        missing_speed = 0
        for _, _, d in G.edges(data=True):
            if 'length' not in d:
                missing_length += 1
            if 'speed_kmph' not in d:
                missing_speed += 1

        if missing_length > 0:
            raise Exception(f"found {missing_length} links in the road network that don't have length information")
        elif missing_speed > 0:
            log.warning(f"found {missing_speed} links in the road network that don't have speed information.\n"
                        f"hive will automatically set these to {self.default_speed_kmph} kmph.")

        self.G = G
        self._nodes = [nid for nid in self.G.nodes()]
        self.geoid_to_node_id = geoid_to_node_id
        self.kdtree = self._build_kdtree()

    def _build_kdtree(self) -> cKDTree:
        try:
            points = [(self.G.nodes[nid]['y'], self.G.nodes[nid]['x']) for nid in self._nodes]
        except KeyError:
            try:
                points = [(self.G.nodes[nid]['lat'], self.G.nodes[nid]['lon']) for nid in self._nodes]
            except KeyError:
                raise Exception("node attributes must have either (y, x) or (lat, lon) information")

        tree = cKDTree(np.array(points))

        return tree

    def _route_attributes(
            self,
            route: list,
            attribute: str = None,
            minimize_key: str = 'length',
    ) -> Tuple[Dict[str, str], ...]:
        """
        Taken from osmnx package, geo_utils module.


        :param route: the route to get attributes for

        :param attribute: the attribute of interest. will return all attributes if None

        :param minimize_key: the key to minimize over if multiple edges exist between two nodes
        :return: a tuple of attributes
        """

        attribute_values = ()
        for u, v in zip(route[:-1], route[1:]):
            # if there are parallel edges between two nodes, select the one with the
            # lowest value of minimize_key
            data = min(self.G.get_edge_data(u, v).values(), key=lambda x: x[minimize_key])
            if attribute is None:
                attribute_value = data
            else:
                attribute_value = data[attribute]
            attribute_values = attribute_values + (attribute_value,)
        return attribute_values

    def _generate_route_start(self, origin_node_id, origin_geoid) -> Route:
        """
        Generates the starting link for a case when the origin geoid is not at a node


        :param node_id: the origin node id
        :return: the starting link of a route
        """
        node = self.G.nodes[origin_node_id]

        if origin_geoid == node['geoid']:
            # we're already there
            return ()

        link_id = "start-" + str(origin_node_id)
        distance_km = H3Ops.great_circle_distance(origin_geoid, node['geoid'])

        link = Link(
            link_id=link_id,
            start=origin_geoid,
            end=node['geoid'],
            distance_km=distance_km,
            speed_kmph=self.default_speed_kmph,
        )

        return (link,)

    def route(self, origin: GeoId, destination: GeoId) -> Route:
        """
        Returns a route containing road network links between the origin and destination geoids.

        Right now, the origin and destination are snapped to the nearest network node.

        # TODO: consider implementing a way to snap incoming points to the nearest edge intersection.


        :param origin: the geoid of the origin

        :param destination: the geoid of the destination
        :return: a route between the origin and destination
        """
        if origin in self.geoid_to_node_id:
            # no need to search for nearest node since we already have it
            origin_node = self.geoid_to_node_id[origin]
        else:
            # find the closest node on the network
            lat, lon = h3.h3_to_geo(origin)
            origin_node = self.get_nearest_node(lat, lon)

        if destination in self.geoid_to_node_id:
            destination_node = self.geoid_to_node_id[destination]
        else:
            lat, lon = h3.h3_to_geo(destination)
            destination_node = self.get_nearest_node(lat, lon)

        nx_route = nx.shortest_path(self.G, origin_node, destination_node)
        route_attributes = self._route_attributes(nx_route)

        route = self._generate_route_start(nx_route[0], origin)

        for i in range(len(nx_route) - 1):
            nid_1 = nx_route[i]
            nid_2 = nx_route[i + 1]

            link_id = str(nid_1) + "-" + str(nid_2)
            distance_km = route_attributes[i]['length'] * M_TO_KM

            try:
                speed_kmph = route_attributes[i]['speed_kmph']
            except KeyError:
                log.debug(f"found a road network link without any speed information, "
                            f"using default speed of {self.default_speed_kmph} kmph")
                speed_kmph = self.default_speed_kmph

            link = Link(
                link_id=link_id,
                start=self.G.nodes[nid_1]['geoid'],
                end=self.G.nodes[nid_2]['geoid'],
                distance_km=distance_km,
                speed_kmph=speed_kmph,
            )

            route = route + (link,)

        return route

    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        """
        Returns the road network distance between the origin and destination


        :param origin: the geoid of the origin

        :param destination: the geoid of the destination
        :return: the road network distance in kilometers
        """
        distance = route_distance_km(self.route(origin, destination))
        return distance

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        Returns a link from a single geoid. This link has the same origin and destination and
        has a speed and distance of 0. These links are used to map static objects to the road network.


        :param geoid: the geoid to snap to the road newtork
        :return: the link on the road network that is closest to the geoid
        """
        if geoid in self.geoid_to_node_id:
            nid = self.geoid_to_node_id[geoid]
        else:
            lat, lon = h3.h3_to_geo(geoid)
            nid = self.get_nearest_node(lat, lon)

        return Link(
            link_id=str(nid) + "-" + str(nid),
            start=self.G.nodes[nid]['geoid'],
            end=self.G.nodes[nid]['geoid'],
            distance_km=0,
            speed_kmph=0,
        )

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        Determines if a specific geoid is contained within the road network geofence.


        :param geoid: the geoid to test
        :return: True/False
        """
        return True
        # TODO: the geofence is slated to be modified and so we're bypassing this check in the meantime.
        #  we'll need to add it back once we update the geofence implementation.

        # if not self.geofence:
        #     raise RuntimeError("Geofence not specified.")
        # else:
        #     return self.geofence.contains(geoid)

    def get_nearest_node(self, lat, lon) -> str:
        _, i = self.kdtree.query([lat, lon])
        return self._nodes[int(i)]

    def update(self, sim_time: SimTime) -> RoadNetwork:
        raise NotImplementedError("updates are not implemented")
