from __future__ import annotations

import functools as ft
from typing import Union

import immutables
from networkx.classes.reportviews import NodeView

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.link_id import *
from hive.model.roadnetwork.route import Route


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
                acc: Tuple[Optional[Exception], Optional[Tuple[Link, ...]]],
                node_id_pair: Tuple[int, int]
        ) -> Tuple[Optional[Exception], Optional[Tuple[Link, ...]]]:
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
                    updated_links = prev_links + (link,)
                    return None, updated_links

        nx_path_adj_pairs = [(nx_path[i], nx_path[i+1]) for i in range(0, len(nx_path) - 1)]
        initial = None, ()
        result = ft.reduce(_accumulate_links, nx_path_adj_pairs, initial)
        return result


def resolve_route_src_dst_positions(
        inner_route: Route,
        src_link_pos: Link,
        dst_link_pos: Link,
        road_network: 'OSMRoadNetwork') -> Optional[Route]:
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
    src_link_updated = src_link.update_start(src_link_pos.start) if src_link else None
    dst_link_updated = dst_link.update_end(dst_link_pos.end) if dst_link else None
    if not src_link_updated or not dst_link_updated:
        return None
    else:
        # for any length inner route, form the total route by attaching these
        # start and end links whose start or end values have been modified to
        # align with the search start/end locations
        updated_route = (src_link_updated,) + inner_route + (dst_link_updated,)
        return updated_route
