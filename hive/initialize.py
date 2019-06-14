import sys
import numpy as np
import random

from hive import charging as chrg
from hive import tripenergy as nrg
from hive.stations import FuelStation, VehicleBase
from hive.vehicle import Vehicle

def initialize_stations(station_df, station_log_file):
    stations = []
    for i, row in station_df.iterrows():
        station_id = row['station_id']
        lon, lat = row['longitude'], row['latitude']
        plugs = row['plugs']
        plug_type = row['plug_type']
        plug_power = row['plug_power_kw']
        station = FuelStation(station_id,
                              lat,
                              lon,
                              plugs,
                              plug_type,
                              plug_power,
                              station_log_file)
        stations.append(station)

    return stations

def initialize_bases(base_df, base_log_file):
    bases = []
    base_power_dict = {}
    for i, row in base_df.iterrows():
        base_id = row['base_id']
        lon, lat = row['longitude'], row['latitude']
        plugs = row['plugs']
        plug_type = row['plug_type']
        plug_power = row['plug_power_kw']
        station = VehicleBase(base_id,
                               lat,
                               lon,
                               plugs,
                               plug_type,
                               plug_power,
                               base_log_file)
        bases.append(base)
        base_power_dict[base_id] = {'type': plug_type,
                                    'kw': plug_power}

    return bases, base_power_dict


def initialize_fleet(vehicle_types, bases, charge_curve, whmi_lookup, env_params, vehicle_log_file):
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
                        max_passengers = veh_type.PASSENGERS,
                        initial_soc = np.random.uniform(0.2, 1.0), #init vehs w/ uniform soc distr
                        whmi_lookup = scaled_whmi_lookup,
                        charge_template = charge_template,
                        logfile = vehicle_log_file,
                        environment_params = env_params,
                        )
            id += 1

            #Initialize vehicle location to a random base
            base = random.choice(bases) # @NR - are we passing a single seed throughout HIVE for reproduceability?
            veh.avail_lat = base.LAT
            veh.avail_lon = base.LON
            veh.base = base.base_id

            veh_fleet.append(veh)

    random.shuffle(veh_fleet)
    return veh_fleet
