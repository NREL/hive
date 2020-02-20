from __future__ import annotations

import osmnx as ox
import networkx as nx
from h3 import h3

from typing import Tuple, Optional, Dict

from networkx.classes.multidigraph import MultiDiGraph

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.geofence import GeoFence
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers, M_TO_KM, MPH_TO_KMPH


class OSMRoadNetwork(RoadNetwork):
    """
    Implements an open street maps road network utilizing the osmnx and networkx libraries
    """

    def __init__(
            self,
            road_network_file: str,
            geofence: Optional[GeoFence] = None,
            sim_h3_resolution: H3Resolution = 15,
    ):
        self.sim_h3_resolution = sim_h3_resolution
        self.geofence = geofence

        G, geoid_to_node_id = self._parse_road_network_graph(ox.graph_from_file(road_network_file))

        self.G = G
        self.geoid_to_node_id = geoid_to_node_id

    def _parse_road_network_graph(self, g: MultiDiGraph) -> Tuple[MultiDiGraph, Dict]:
        if not nx.is_strongly_connected(g):
            raise RuntimeError("Only strongly connected graphs are allowed.")
        geoid_map = {}
        geoid_to_node_id = {}
        for nid in g.nodes():
            node = g.nodes[nid]
            geoid = h3.geo_to_h3(node['y'], node['x'], res=self.sim_h3_resolution)
            geoid_map[nid] = {'geoid': geoid}
            geoid_to_node_id[geoid] = nid

        nx.set_node_attributes(g, geoid_map)

        return g, geoid_to_node_id

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
            origin_node = ox.get_nearest_node(self.G, (lat, lon))

        if destination in self.geoid_to_node_id:
            destination_node = self.geoid_to_node_id[destination]
        else:
            lat, lon = h3.h3_to_geo(destination)
            destination_node = ox.get_nearest_node(self.G, (lat, lon))

        nx_route = nx.shortest_path(self.G, origin_node, destination_node)
        route_attributes = ox.get_route_edge_attributes(self.G, nx_route)

        if len(nx_route) == 1:
            # special case in which the origin and destination correspond to the same node on the network
            nid_1 = nx_route[0]

            link = Link(
                link_id=str(nid_1) + "-" + str(nid_1),
                start=self.G.nodes[nid_1]['geoid'],
                end=self.G.nodes[nid_1]['geoid'],
                distance_km=0,
                speed_kmph=0,
            )

            return (link,)

        route = ()

        for i in range(len(nx_route) - 1):
            nid_1 = nx_route[i]
            nid_2 = nx_route[i + 1]

            link_id = str(nid_1) + "-" + str(nid_2)
            distance_km = route_attributes[i]['length'] * M_TO_KM
            speed_string = route_attributes[i]['maxspeed']

            # TODO: implement more robust parsing
            # maxspeed comes in several variants:
            #   - 'nan'
            #   - 'X mph'
            #   - 'X kmph'
            #   - '['nan', 'X mph']

            if speed_string == 'nan':
                speed_kmph = 40
            elif '[' in speed_string:
                speed_kmph = 40
            elif isinstance(speed_string, list):
                speed_kmph = 40
            elif 'mph' in speed_string:
                speed_mph = float(speed_string.split(' ')[0])
                speed_kmph = speed_mph * MPH_TO_KMPH
            else:
                speed_kmph = float(speed_string.split(' ')[0])

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
        route = self.route(origin, destination)
        distance_km = 0
        for link in route:
            distance_km += link.distance_km
        return distance_km

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
            nid = ox.get_nearest_node(self.G, (lat, lon))

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
        if not self.geofence:
            raise RuntimeError("Geofence not specified.")
        else:
            return self.geofence.contains(geoid)
