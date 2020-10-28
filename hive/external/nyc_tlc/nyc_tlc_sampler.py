import json
import random
from csv import DictReader, DictWriter

import h3
from pkg_resources import resource_filename

from hive.external.nyc_tlc.nyc_tlc_parsers import parse_yellow_tripdata_row
from hive.util.units import KwH, Kw


def down_sample_nyc_tlc_data(in_file: str,
                             out_file: str,
                             sample_size: int,
                             request_cancel_time_buffer: int = 300,
                             sim_h3_location_resolution: int = 15,
                             boundary_h3_resolution: int = 10):
    """
    down-samples in input_config TLC data file for Yellow cab data


    :param in_file: the source TLC data file

    :param out_file: a file in HIVE Request data format

    :param sample_size: number of agents to sample - performs no randomization

    :param request_cancel_time_buffer: the cancel time to set on each agent

    :param sim_h3_location_resolution:

    :param boundary_h3_resolution: the resolution for the bounding set of the nyc polygon
    :return:
    """

    # this could clearly be generalized for other polygons/request sets
    with open(resource_filename("hive.resources.geofence", "nyc_single_polygon.geojson")) as f:

        # needs to be a Polygon, not a MultiPolygon feature
        # used for ETL to confirm that requests sampled are in fact within the study area (some are not)
        geojson = json.load(f)
        hexes = h3.polyfill(
            geojson=geojson['geometry'],
            res=boundary_h3_resolution,
            geo_json_conformant=True
        )

        with open(in_file) as f:
            with open(out_file, 'w', newline='') as w:
                reader = DictReader(f)
                header = [
                    'request_id',
                    'o_lat',
                    'o_lon',
                    'd_lat',
                    'd_lon',
                    'departure_time',
                    'passengers'
                ]

                writer = DictWriter(w, header)
                writer.writeheader()

                # while loop state
                attempted_count = 0
                absolute_cutoff = sample_size * 2  # arbitrary cutoff here; errors should be few
                recorded_count = 0

                while recorded_count < sample_size and attempted_count < absolute_cutoff:
                    # parse the next row of data
                    row = next(reader)
                    req = parse_yellow_tripdata_row(
                        row,
                        recorded_count,
                        request_cancel_time_buffer,
                        sim_h3_location_resolution
                    )

                    if not isinstance(req, Exception) and h3.h3_to_parent(req.geoid, boundary_h3_resolution) in hexes:
                        # request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
                        out_row = {
                            'request_id': req.id,
                            'o_lat': row['pickup_latitude'],
                            'o_lon': row['pickup_longitude'],
                            'd_lat': row['dropoff_latitude'],
                            'd_lon': row['dropoff_longitude'],
                            'departure_time': req.departure_time,
                            'passengers': len(req.passengers)
                        }
                        writer.writerow(out_row)
                        recorded_count += 1
                    else:
                        print(f"row for id {recorded_count} failed: {row}")

    if attempted_count == absolute_cutoff:
        raise IOError(f"too many errors, input_config file {in_file} (and corresponding file {out_file}) may be corrupt")


def sample_vehicles_in_geofence(num: int,
                                out_file: str,
                                powertrain_id: str,
                                powercurve_id: str,
                                capacity: KwH,
                                initial_soc: float,
                                ideal_energy_limit: KwH,
                                max_charge_acceptance_kw: Kw):
    """
    samples points in the NYC polygon and creates Vehicles from them, writing to an output file

    :param num: number of vehicles

    :param out_file: the file to write the vehicles

    :param powertrain_id:

    :param powercurve_id:

    :param capacity:

    :param initial_soc:

    :param ideal_energy_limit:

    :param max_charge_acceptance_kw:
    """

    # load geojson file with boundary polygon
    with open(resource_filename("hive.resources.geofence", "nyc_single_polygon.geojson")) as f:

        # needs to be a Polygon, not a MultiPolygon feature
        geojson = json.load(f)
        hexes = list(h3.polyfill(
            geojson=geojson['geometry'],
            res=10,
            geo_json_conformant=True)
        )

        with open(out_file, 'w', newline='') as w:
            header = ["vehicle_id", "lat", "lon", "powertrain_id", "powercurve_id", "capacity", "ideal_energy_limit",
                      "max_charge_acceptance", "initial_soc"]

            writer = DictWriter(w, header)
            writer.writeheader()
            for i in range(0, num):
                vehicle_id = f"v{i}"

                random_upper_hex = random.choice(hexes)
                children = list(h3.h3_to_children(random_upper_hex, 15))
                random_lower_hex = random.choice(children)
                lat, lon = h3.h3_to_geo(random_lower_hex)

                row = {
                    'vehicle_id': vehicle_id,
                    'lat': lat,
                    'lon': lon,
                    'powertrain_id': powertrain_id,
                    'powercurve_id': powercurve_id,
                    'capacity': capacity,
                    'initial_soc': initial_soc,
                    'ideal_energy_limit': ideal_energy_limit,
                    'max_charge_acceptance': max_charge_acceptance_kw
                }

                writer.writerow(row)
