from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, NamedTuple

import h3
import immutables
from networkx import MultiDiGraph
from scipy.spatial.ckdtree import cKDTree

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.link_id import create_link_id
from hive.model.roadnetwork.osm.osm_roadnetwork_ops import safe_get_node_coordinates
from hive.util.typealiases import GeoId, LinkId
from hive.util.units import M_TO_KM, Kmph, Kilometers


class OSMRoadNetworkLinkHelper(NamedTuple):
    """
    provides indexing functionality for an OSMRoadNetwork
    :param links: the lookup table for all road network Links by their LinkId
    :param links_spatial_lookup: a spatial tree lookup for the nearest link search. returns an index
                                 to the links_linkid_lookup collection
    :param links_linkid_lookup: used in conjunction with the cKDTree to provide the LinkId of the nearest Link
    :param link_count: the count of links
    """
    links: immutables.Map[LinkId, Link]
    links_spatial_lookup: cKDTree
    links_linkid_lookup: Tuple[LinkId, ...]
    link_count: int

    def link_by_geoid(self, geoid: GeoId) -> Tuple[Optional[Exception], Optional[Link]]:
        """
        uses the CKDTree to find a nearest Link to some geoid

        :param geoid: the geoid to query
        :return: an error or the nearest link to this GeoId
        """
        try:
            query = h3.h3_to_geo(geoid)
            _, index_result = self.links_spatial_lookup.query(query)
            index = int(index_result)
            link_id = self.links_linkid_lookup[index] if 0 <= index < self.link_count else None
            link = self.links.get(link_id) if link_id else None
            if not link_id or not link:
                return Exception(f"internal error on nearest link for geoid {geoid}: resulting spatial index value '{index}' is invalid"), None
            else:
                return None, link

        except Exception as e:
            return e, None

    @classmethod
    def build(
            cls,
            graph: MultiDiGraph,
            sim_h3_resolution: int,
            default_speed_kmph: Kmph = 40.0,
            default_distance_km: Kilometers = 0.01) -> Tuple[Optional[Exception], Optional[OSMRoadNetworkLinkHelper]]:
        """
        reads in the graph links from a networkx graph and builds a table with Links by LinkId
        :param graph: the input graph
        :param sim_h3_resolution: h3 resolution for entities in sim
        :param default_speed_kmph: default link speed for unlabeled links
        :param default_distance_km: default link length for unlabeled links
        :return: either an error, or, the lookup table
        """

        class Accumulator(NamedTuple):
            """
            builds data structures used to provide lookup features in the road network

            :param lookup: each Link by it's LinkId
            :param link_ids: link ids which share a common array index to the link_centroids
            :param link_centroids: link centroids (lat,lon) which share a common array index to the link_ids
            """

            lookup: immutables.Map[LinkId, Link] = immutables.Map()
            link_ids: Tuple[LinkId, ...] = ()
            link_centroids: Tuple[Tuple[float, float], ...] = ()

            def add_link(self, link: Link) -> Tuple[Optional[Exception], Optional[Accumulator]]:
                """
                adding a link to this accumulator creates an entry in the data structures used to
                run spatial queries over the graph edge space
                :param link: the link to add
                :return: an error or updated accumulator
                """
                try:
                    h3_line = h3.h3_line(link.start, link.end)

                    # we want to look up edges by their midpoint. that said, two edges will share the same
                    # endpoints, one for each direction. since these two edges would share the same midpoint,
                    # we aim here to make both centroids _just barely_ different by subtracting the midpoint index by 1.
                    midpoint_h3_line_index = round(len(h3_line) / 2) if len(h3_line) > 0 else None
                    src_oriented_midpoint_index = midpoint_h3_line_index - 1 if midpoint_h3_line_index > 0 else midpoint_h3_line_index
                    midpoint_hex = h3_line[src_oriented_midpoint_index] if src_oriented_midpoint_index else link.start
                    link_centroid_lat, link_centroid_lon = h3.h3_to_geo(midpoint_hex)
                    updated_acc = self._replace(
                        lookup=self.lookup.set(link.link_id, link),
                        link_ids=self.link_ids + (link.link_id,),
                        link_centroids=self.link_centroids + ((link_centroid_lat, link_centroid_lon),)
                    )
                    return None, updated_acc
                except Exception as e:
                    return e, None

        # inner loop function that attaches a LinkId -> Link pair to a Map
        def create_link_entry(
                acc: Tuple[Optional[Exception], Optional[Accumulator]],
                link_tuple: Tuple[int, int, int]) -> Tuple[Optional[Exception], Optional[Accumulator]]:
            acc_error, accumulator = acc
            if acc_error:
                return acc
            else:
                try:
                    src, dst, _ = link_tuple
                    link_id = create_link_id(src, dst)
                    src_node = graph.nodes[src]
                    dst_node = graph.nodes[dst]
                    src_coord_err, src_coord = safe_get_node_coordinates(src_node, src)
                    dst_coord_err, dst_coord = safe_get_node_coordinates(dst_node, dst)
                    if src_coord_err:
                        response = Exception(f"failure getting node coordinates while building OSMRoadNetworkLinkHelper")
                        response.__cause__ = src_coord_err
                        return response, None
                    elif dst_coord_err:
                        response = Exception(f"failure getting node coordinates while building OSMRoadNetworkLinkHelper")
                        response.__cause__ = dst_coord_err
                        return response, None
                    else:
                        src_lat, src_lon = src_coord
                        dst_lat, dst_lon = dst_coord
                        src_geoid = h3.geo_to_h3(src_lat, src_lon, resolution=sim_h3_resolution)
                        dst_geoid = h3.geo_to_h3(dst_lat, dst_lon, resolution=sim_h3_resolution)
                        data = graph.get_edge_data(src, dst, 0, None)  # data index "0" as this uses networkx's multigraph implementation
                        speed = data.get('speed_kmph', default_speed_kmph) if data else default_speed_kmph
                        distance_miles = data.get('length', default_distance_km) if data else default_distance_km
                        distance = distance_miles * M_TO_KM if distance_miles else default_distance_km
                        link = Link.build(link_id, src_geoid, dst_geoid, speed, distance)
                        add_link_error, updated_accumulator = accumulator.add_link(link)
                        if add_link_error:
                            response = Exception(f"failure adding link while building OSMRoadNetworkLinkHelper")
                            response.__cause__ = add_link_error
                            return response, None
                        else:
                            return None, updated_accumulator
                except Exception as e:
                    return e, None

        # process each link, building the collection of Links by LinkId, and
        # the collections which will be used to build a spatial index over the edge centroids
        initial = None, Accumulator()
        error, accumulator = ft.reduce(create_link_entry, graph.edges, initial)
        if error:
            response = Exception(f"failure building OSMRoadNetworkLinkHelper")
            response.__cause__ = error
            return response, None
        else:
            # construct the spatial index
            tree = cKDTree(accumulator.link_centroids)
            osm_road_network_links = OSMRoadNetworkLinkHelper(accumulator.lookup, tree, accumulator.link_ids, len(accumulator.link_ids))
            return None, osm_road_network_links
