import sys
import numpy as np
import random

from hive import charging as chrg
from hive import tripenergy as nrg
from hive.station import FuelStation
from hive.vehicle import Vehicle

sys.path.append('../')
import config as cfg

def initialize_charge_network(charge_df, station_log_file):

    stations, depots = [], []
    for i, row in charge_df.iterrows():
        station_id = row['station_id']
        station_type = row['station_type']
        lon, lat = row['longitude'], row['latitude']
        plugs = row['plugs']
        plug_type = row['plug_type']
        plug_power = row['plug_power_kw']

        if station_type == 'station':
            station = FuelStation(station_id,
                                    lat,
                                    lon,
                                    plugs,
                                    plug_type,
                                    plug_power,
                                    station_log_file)
            stations.append(station)
        elif station_type == 'depot':
            depot = FuelStation(station_id,
                                lat,
                                lon,
                                plugs,
                                plug_type,
                                plug_power, station_log_file)
            depots.append(depot)

    assert len(stations) > 0, "Must have at least one charge station to run simulation"
    assert len(depots) > 0, "Must have at least one depot to run simulation"

    return stations, depots

def initialize_fleet(vehicle_types, depots, charge_curve, whmi_lookup, env_params, vehicle_log_file):
    id = 1
    veh_fleet = []
    for veh_type in vehicle_types:
        charge_template = chrg.construct_temporal_charge_template(
                                                    charge_curve,
                                                    veh_type.BATTERY_CAPACITY,
                                                    veh_type.CHARGE_ACCEPTANCE,
                                                    )
        scaled_whmi_lookup = nrg.create_scaled_whmi(
                                    whmi_lookup,
                                    veh_type.EFFICIENCY,
                                    )

        for v in range(veh_type.NUM_VEHICLES):
            veh = Vehicle(
                        veh_id = id,
                        name = veh_type.VEHICLE_NAME,
                        battery_capacity = veh_type.BATTERY_CAPACITY,
                        initial_soc = np.random.uniform(0.2, 1.0), #init vehs w/ uniform soc distr
                        whmi_lookup = scaled_whmi_lookup,
                        charge_template = charge_template,
                        logfile = vehicle_log_file,
                        environment_params = env_params,
                        )
            id += 1

            #Initialize vehicle location to a random depot
            depot = random.choice(depots)
            veh.avail_lat = depot.LAT
            veh.avail_lon = depot.LON

            veh_fleet.append(veh)

    random.shuffle(veh_fleet)
    return veh_fleet
