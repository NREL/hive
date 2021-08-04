from __future__ import annotations

import functools as ft
import math
from typing import Union, TYPE_CHECKING
import logging

import immutables
from networkx import MultiDiGraph
from networkx.classes.reportviews import NodeView

from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.link_id import *
from hive.model.roadnetwork.linktraversal import LinkTraversal
from hive.model.roadnetwork.route import Route

if TYPE_CHECKING:
    from hive.model.roadnetwork import OSMRoadNetwork

log = logging.getLogger(__name__)

def safe_get_node_coordinates(node: NodeView, node_id: int) -> Tuple[Optional[Exception], Optional[Tuple[float, float]]]:
    """
    attempts to extract lat/lon location from a graph node attribute
    :param node: the node attribute
    :param node_id: the node id
    :return: coordinate in lat/lon (y/x) ordering, or, an error
    """
    try:
        return None, (node['y'], node['x'])
    except KeyError:
        try:
            return None, (node['lat'], node['lon'])
        except KeyError:
            return KeyError(f"node {node_id} does not have either (y, x) or (lat, lon) information"), None


def route_from_nx_path(nx_path: Union[list, dict], link_lookup: immutables.Map[LinkId, Link]) -> Tuple[Optional[Exception], Optional[Route]]:
    """
    takes a networkx shortest path result (a list of node ids) and turns it into a Route (list of Links)
    :param nx_path: the networkx path result
    :param link_lookup: a table of Links by LinkId in this simulation
    :return: an error, or, the resulting Route
    """
    if len(nx_path) == 1:
        # when origin node == destination node in the networkx shortest path query,
        # the result is a single node. since our graph is edge-oriented, this corresponds
        # with an empty route.
        return None, ()
    else:
        def _accumulate_links(
                acc: Tuple[Optional[Exception], Optional[Tuple[LinkTraversal, ...]]],
                node_id_pair: Tuple[int, int]
        ) -> Tuple[Optional[Exception], Optional[Tuple[LinkTraversal, ...]]]:
            err, prev_links = acc
            if err:
                return acc
            else:
                # build a LinkId from the node pair, then look up the associated Link and return it
                src, dst = node_id_pair
                link_id = create_link_id(src, dst)
                link = link_lookup.get(link_id)
                if not link:
                    link_err = Exception(f"networkx shortest path traverses link id {link_id} which does not exist")
                    return link_err, None
                else:
                    updated_links = prev_links + (link.to_link_traversal(),)
                    return None, updated_links

        nx_path_adj_pairs = [(nx_path[i], nx_path[i+1]) for i in range(0, len(nx_path) - 1)]
        initial = None, ()
        result = ft.reduce(_accumulate_links, nx_path_adj_pairs, initial)
        return result


def resolve_route_src_dst_positions(
        inner_route: Route,
        src_link_pos: EntityPosition,
        dst_link_pos: EntityPosition,
        road_network: OSMRoadNetwork) -> Optional[Route]:
    """
    our inner_route is a shortest path from the destination of the source link to the start
    of the destination link. a 'positional' Link has been provided in the search query, assumed
    to represent the static road network location of some entities. to complete the route,
    the origin and destination links must be attached in a way that their start/end locations
    correspond with the query entities.

    :param inner_route: the result of a shortest path search
    :param src_link_pos: the positional Link representation of an Entity
    :param dst_link_pos: the positional Link representation of another Entity
    :param road_network: the underlying OSM road network state
    :return: a route if it is valid, otherwise None
    """
    src_link = road_network.link_helper.links.get(src_link_pos.link_id)
    dst_link = road_network.link_helper.links.get(dst_link_pos.link_id)
    if not src_link or not dst_link:
        return None
    else:
        # for any length inner route, form the total route by attaching these
        # start and end links whose start or end values have been modified to
        # align with the search start/end locations
        src_link_traversal = src_link.to_link_traversal().update_start(src_link_pos.geoid)
        dst_link_traversal = dst_link.to_link_traversal().update_end(dst_link_pos.geoid)
        updated_route = (src_link_traversal,) + inner_route + (dst_link_traversal,)
        return updated_route


def assign_travel_times(graph: MultiDiGraph):
    """
    adds a travel time to each link on the network with 'length' and 'speed_kmph'
    fills missing data with the average observed link travel time

    :param graph: the graph, updated in-place as a side effect
    """

    # set travel_time attributes, collect all observed lengths + speeds
    acc_length = 0.0
    acc_speed = 0.0
    count = 0
    for u, v, w in graph.edges:

        data = graph.get_edge_data(u, v)
        length = data.get('length') # meters
        speed = data.get('speed_kmph') #kmph
        if length is not None and speed is not None:
            travel_time = (length * 0.001) / speed * 3600 # seconds
            data['travel_time'] = travel_time
            acc_length += length
            acc_speed += speed
            count += 1


    if count > 0:

        # some edges do not have speed or length entries
        # compute average travel time, assign to rows missing length/speed values
        avg_length = acc_length / count
        avg_speed = acc_speed / count
        avg_travel_time = (avg_length * 0.001) / avg_speed * 3600 # seconds

        log.info(f"assigning mean travel time of {avg_travel_time} seconds to {count} links with missing attributes")

        for u, v, w in graph.edges:
            data = graph.get_edge_data(u, v)
            travel_time = data.get('travel_time')
            if travel_time is None:
                data['travel_time'] = avg_travel_time


def euclidean_distance_heuristic(graph):
    """
    A* Search heuristic

    :param graph: road network graph
    :param a: a node id
    :param b: another node id
    :return: the Euclidean distance function between a and b using their lat/lon coordinates in this graph
    """
    def _inner(a, b):
        a_data = graph.nodes.get(a)
        b_data = graph.nodes.get(b)
        dist = math.sqrt(math.pow(a_data['x'] - b_data['x'], 2) + math.pow(a_data['y'] - b_data['y'], 2))
        return dist

    return _inner