from pathlib import Path
import geopandas as gpd
import argparse
from nrel.hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork

# this example script builds a HIVE road network using OSMNx and GeoPandas
# and can be called from the command line via
# `$ python download_road_network.py some_boundary.geojson`
# under the hood, HIVE will call OSMNx and build the road network with some
# simple rules for downloading and reading the OSM data. for more complex
# network parsing rules you will need to build your own process.

parser = argparse.ArgumentParser(description="network builder")
parser.add_argument(
    "boundary",
    type=Path,
    help="GeoJSON boundary file describing the extent of the network to load",
)
parser.add_argument(
    "--outfile",
    type=Path,
    default="network.json",
    help="file path to use when writing the HIVE network",
)


def import_network(geojson_file: Path, outfile: Path):
    """builds a road network for HIVE from the provided source GeoJSON.
    a simple wrapper around reading the GeoJSON via GeoPandas and then
    calling HIVE's OSM network reader.
    depends on OSMNx: https://github.com/gboeing/osmnx

    :param geojson_file: file containing network boundary
    :type geojson_file: Path
    :param outfile: _description_
    :type outfile: Path
    """
    df = gpd.read_file(geojson_file)
    polygon = df.geometry.unary_union
    rn = OSMRoadNetwork.from_polygon(polygon)

    rn.to_file(outfile)


if __name__ == "__main__":
    args = parser.parse_args()
    import_network(args.boundary, args.outfile)
