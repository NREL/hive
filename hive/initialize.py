import sys
import os
import numpy as np
import random
import datetime

from hive import charging as chrg
from hive import tripenergy as nrg
from hive.stations import FuelStation
from hive.vehicle import Vehicle
from hive.utils import initialize_log


def initialize_stations(station_df, clock):
    """
    Initializes stations dict from DataFrame.

    Function initializes stations dict from pd.DataFrame containing vehicle
    station network .csv (hive/inputs/charge_network/..).

    Parameters
    ----------
    station_df: pd.DataFrame
        DataFrame containing scenario vehicle base network
    station_log_file: string
        File for logging

    Returns
    -------
    stations
        list of initialized stations.
    """
    stations = []
    for station in station_df.itertuples():
        station = FuelStation(station.id,
                              station.latitude,
                              station.longitude,
                              station.plugs,
                              station.plug_type,
                              station.plug_power_kw,
                              clock,
                              )
        stations.append(station)

    return stations

def initialize_fleet(vehicle_types,
                        bases,
                        charge_curve,
                        whmi_lookup,
                        start_time,
                        env_params,
                        clock,
                        ):
    id = 0
    veh_fleet = []
    fleet_state_constructor = []
    for veh_type in vehicle_types:
        charge_template = chrg.construct_temporal_charge_template(
                                                    charge_curve,
                                                    veh_type.BATTERY_CAPACITY_KWH,
                                                    veh_type.MAX_KW_ACCEPTANCE,
                                                    )
        scaled_whmi_lookup = nrg.create_scaled_whmi(
                                    whmi_lookup,
                                    veh_type.EFFICIENCY_WHMI,
                                    )

        for _ in range(veh_type.NUM_VEHICLES):
            veh = Vehicle(
                        veh_id = id,
                        name = veh_type.VEHICLE_NAME,
                        battery_capacity = veh_type.BATTERY_CAPACITY_KWH,
                        max_charge_acceptance = veh_type.MAX_KW_ACCEPTANCE,
                        max_passengers = veh_type.PASSENGERS,
                        whmi_lookup = scaled_whmi_lookup,
                        charge_template = charge_template,
                        clock = clock,
                        environment_params = env_params,
                        )

            id += 1

            #Initialize vehicle location to a random base
            base = random.choice(bases)

            veh.latlon = (base.LAT, base.LON)
            veh.base = base

            veh.avail_time = start_time - datetime.timedelta(hours=1)

            avg_kwh__mi = np.average(scaled_whmi_lookup['whmi']) / 1000

            veh_fleet.append(veh)

            #TODO: Make this more explicit
            fleet_state_constructor.append((veh.x,
                                            veh.y,
                                            1,
                                            1,
                                            0,
                                            0,
                                            avg_kwh__mi,
                                            veh.BATTERY_CAPACITY,
                                            veh.MAX_PASSENGERS))

    fleet_state = np.array(fleet_state_constructor)

    for veh in veh_fleet:
        veh.fleet_state = fleet_state
        veh.energy_kwh = np.random.uniform(0.05, 1.0) * veh.BATTERY_CAPACITY

    return veh_fleet, fleet_state
