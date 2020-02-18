from __future__ import annotations

import osmnx as ox
import networkx as nx
from h3 import h3

from typing import Tuple, Optional

from networkx.classes.multidigraph import MultiDiGraph

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.geofence import GeoFence
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers, M_TO_KM, MPH_TO_KMPH


class OSMRoadNetwork(RoadNetwork):
    """
    Implements an open street maps road network utilizing the osmnx library
    """

    def __init__(
            self,
            road_network_file: str,
            geofence: Optional[GeoFence] = None,
            sim_h3_resolution: H3Resolution = 15,
    ):
        self.sim_h3_resolution = sim_h3_resolution
        self.geofence = geofence

        G, geoid_to_node_id = self._map_node_to_geoid(ox.graph_from_file(road_network_file))

        self.G = G
        self.geoid_to_node_id = geoid_to_node_id

    def _map_node_to_geoid(self, g: MultiDiGraph):
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
        if origin in self.geoid_to_node_id:
            origin_node = self.geoid_to_node_id[origin]
        else:
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
        route = self.route(origin, destination)
        distance_km = 0
        for link in route:
            distance_km += link.distance_km
        return distance_km

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
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
        if not self.geofence:
            raise RuntimeError("Geofence not specified.")
        else:
            return self.geofence.contains(geoid)
