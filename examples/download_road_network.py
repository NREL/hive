from pathlib import Path

import json

import geopandas as gpd
import osmnx as ox
import networkx as nx

GEOJSON_PATH = Path(
    "../nrel/hive/resources/scenarios/denver_downtown/geofence/downtown_denver.json"
)
OUTFILE = Path("denver_demo_road_network.json")


def build_road_network(geojson_file: Path, outfile: Path):
    df = gpd.read_file(geojson_file)

    polygon = df.iloc[0].geometry

    # we want to set the configuration to be all one-way.
    # This doesn't eliminate two-way streets but rather returns two distinct one-way edges for each two-way street.
    ox.utils.config(all_oneway=True)

    G = ox.graph_from_polygon(polygon, network_type="drive")

    # hive expects the graph to be strongly connected
    G = ox.utils_graph.get_largest_component(G, strongly=True)

    with outfile.open("w") as f:
        json.dump(nx.node_link_data(G), f)


if __name__ == "__main__":
    build_road_network(GEOJSON_PATH, OUTFILE)