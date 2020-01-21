import json
import random
from csv import DictReader, DictWriter

from h3 import h3
from pkg_resources import resource_filename

from hive.external.nyc_tlc.nyc_tlc_parsers import parse_yellow_tripdata_row
from hive.util.units import KwH, Kw


def down_sample_nyc_tlc_data(in_file: str,
                             out_file: str,
                             sample_size: int,
                             cancel_time: int = 300,
                             sim_h3_location_resolution: int = 15):
    """
    down-samples in input TLC data file for Yellow cab data

    :param in_file: the source TLC data file
    :param out_file: a file in HIVE Request data format
    :param sample_size: number of agents to sample - performs no randomization
    :param cancel_time: the cancel time to set on each agent
    :param sim_h3_location_resolution:
    :return:
    """
    with open(in_file) as f:
        with open(out_file, 'w', newline='') as w:
            reader = DictReader(f)
            header = ['request_id', 'o_lat', 'o_lon', 'd_lat', 'd_lon', 'departure_time', 'cancel_time', 'passengers']
            writer = DictWriter(w, header)
            writer.writeheader()
            i = 0
            while i < sample_size:
                row = next(reader)
                req = parse_yellow_tripdata_row(row, i, cancel_time, sim_h3_location_resolution)
                if not isinstance(req, Exception):
                    # request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
                    out_row = {
                        'request_id': req.id,
                        'o_lat': row['pickup_latitude'],
                        'o_lon': row['pickup_longitude'],
                        'd_lat': row['dropoff_latitude'],
                        'd_lon': row['dropoff_longitude'],
                        'departure_time': req.departure_time,
                        'cancel_time': req.cancel_time,
                        'passengers': len(req.passengers)
                    }
                    writer.writerow(out_row)
                    i += 1
                else:
                    print(f"row for id {i} failed: {row}")


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
            geo_json=geojson['geometry'],
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
                    'capacity': capacity.magnitude,
                    'initial_soc': initial_soc,
                    'ideal_energy_limit': ideal_energy_limit.magnitude,
                    'max_charge_acceptance': max_charge_acceptance_kw.magnitude
                }

                writer.writerow(row)
