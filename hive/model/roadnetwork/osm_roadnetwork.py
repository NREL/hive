from __future__ import annotations

from typing import Tuple, Optional, Dict, Union

import networkx as nx
from h3 import h3
from networkx.classes.multidigraph import MultiDiGraph
from rtree import index

from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route
from hive.util import SimTime
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers, Kmph, M_TO_KM, MPH_TO_KMPH
from hive.external.miniosmnx.core import graph_from_file


class OSMRoadNetwork(RoadNetwork):
    """
    Implements an open street maps road network utilizing the osmnx and networkx libraries
    """
    _unit_conversion = {
        'mph': MPH_TO_KMPH,
        'kmph': 1,
    }

    def __init__(
            self,
            road_network_file: str,
            geofence: Optional[GeoFence] = None,
            sim_h3_resolution: H3Resolution = 15,
            default_speed_kmph: Kmph = 40.0,
    ):
        self.sim_h3_resolution = sim_h3_resolution
        self.geofence = geofence

        self.default_speed_kmph = default_speed_kmph

        G, geoid_to_node_id = self._parse_road_network_graph(graph_from_file(road_network_file))

        self.G = G
        self.geoid_to_node_id = geoid_to_node_id
        self.rtree = self._build_rtree()

    def _build_rtree(self) -> index.Index:
        tree = index.Index()
        nudge = .0000000001
        for nid in self.G.nodes():
            lat = self.G.nodes[nid]['y']
            lon = self.G.nodes[nid]['x']
            tree.insert(nid, (lat-nudge, lon-nudge, lat+nudge, lon+nudge))

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
            attribute_values = attribute_values + (attribute_value, )
        return attribute_values

    def _parse_osm_speed(self, osm_speed: Union[str, list]) -> Kmph:

        # capture any strings that should be lists
        if '[' in osm_speed:
            osm_speed = eval(osm_speed)

        if isinstance(osm_speed, list):
            # if the speed is a list, we'll parse each element and take the lowest speed as a conservative measure.
            min_speed = 10000
            units = None
            for ss in osm_speed:
                speed = float(ss.split(' ')[0])
                if speed < min_speed:
                    min_speed = speed
                    units = ss.split(' ')[1]
            if not units:
                speed_kmph = self.default_speed_kmph
            else:
                speed_kmph = min_speed * self._unit_conversion[units]
        elif isinstance(osm_speed, str):
            if not any(char.isdigit() for char in osm_speed):
                # no numbers in string, set as defualt
                speed_kmph = self.default_speed_kmph
            else:
                # parse the string assuming the format '{speed} {units}'
                speed = float(osm_speed.split(' ')[0])
                units = osm_speed.split(' ')[1]
                speed_kmph = speed * self._unit_conversion[units]
        else:
            # if the speed neither a list nor a string (i.e. None), we set as default
            speed_kmph = self.default_speed_kmph

        return speed_kmph

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

        osm_speed = nx.get_edge_attributes(g, 'maxspeed')
        hive_speed = {k: self._parse_osm_speed(v) for k, v in osm_speed.items()}
        nx.set_edge_attributes(g, hive_speed, 'speed_kmph')

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
            origin_node = self.get_nearest_node(lat, lon)

        if destination in self.geoid_to_node_id:
            destination_node = self.geoid_to_node_id[destination]
        else:
            lat, lon = h3.h3_to_geo(destination)
            destination_node = self.get_nearest_node(lat, lon)

        nx_route = nx.shortest_path(self.G, origin_node, destination_node)
        route_attributes = self._route_attributes(nx_route)

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
            speed_kmph = route_attributes[i]['speed_kmph']

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
        node_id = list(self.rtree.nearest((lat, lon, lat, lon), 1))[0]

        return node_id

    def update(self, sim_time: SimTime) -> RoadNetwork:
        raise NotImplementedError("updates are not implemented")

