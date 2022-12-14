from pathlib import Path

import geopandas as gpd

from nrel.hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork

GEOJSON_PATH = Path(
    "../nrel/hive/resources/scenarios/denver_downtown/geofence/downtown_denver.json"
)
OUTFILE = Path("denver_demo_road_network.json")


def build_road_network(geojson_file: Path, outfile: Path):
    df = gpd.read_file(geojson_file)

    polygon = df.iloc[0].geometry

    rn = OSMRoadNetwork.from_polygon(polygon)

    rn.to_file(OUTFILE)


if __name__ == "__main__":
    build_road_network(GEOJSON_PATH, OUTFILE)
