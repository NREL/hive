from typing import TYPE_CHECKING


def osm_graph_from_polygon(polygon, cache_folder):
    """
    builds a OSM networkx graph using a shapely polygon and the osmnx package
    """
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "the osmnx package is required for building an OSMRoadNetwork from a polygon"
        ) from e

    ox.settings.all_oneway = True
    ox.settings.cache_folder = cache_folder

    G = ox.graph_from_polygon(polygon, network_type="drive")

    G = ox.utils_graph.get_largest_component(G, strongly=True)

    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    # remove any unnecessary information
    for _, _, d in G.edges(data=True):
        if "geometry" in d:
            del d["geometry"]
        if "speed_kph" in d:
            d["speed_kmph"] = d["speed_kph"]
            del d["speed_kph"]
        if "reversed" in d:
            del d["reversed"]
        if "oneway" in d:
            del d["oneway"]
        if "name" in d:
            del d["name"]
        if "highway" in d:
            del d["highway"]
        if "lanes" in d:
            del d["lanes"]
        if "maxspeed" in d:
            del d["maxspeed"]
        if "ref" in d:
            del d["ref"]

    for _, d in G.nodes(data=True):
        if "highway" in d:
            del d["highway"]
        if "street_count" in d:
            del d["street_count"]

    return G
