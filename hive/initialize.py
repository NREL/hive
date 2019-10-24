import sys
import os
import numpy as np
import random
import datetime

from hive import charging as chrg
from hive import tripenergy as nrg
from hive.stations import FuelStation
from hive.vehicle import Vehicle
from hive.vehiclestate import VehicleState


def initialize_stations(station_df, clock, log):
    """
    Initializes stations list from DataFrame.

    Parameters
    ----------
    station_df: pd.DataFrame
        DataFrame containing scenario vehicle station or base network
    clock: hive.utils.Clock
        simulation clock shared across the simulation to track simulation time steps.

    Returns
    -------
    stations: list
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
                              log = log,
                              )
        stations.append(station)

    # write station log header
    if log:
        header = stations[0].LOG_COLUMNS[0]
        for column in stations[0].LOG_COLUMNS[1:]:
            header = header + "," + column
        log.info(header)

    return stations

def initialize_fleet(vehicle_types,
                        bases,
                        charge_curve,
                        whmi_lookup,
                        start_time,
                        env_params,
                        clock,
                        vehicle_log,
                        ):
    """
    Initializes the fleet and the fleet_state matrix.

    Parameters
    ----------
    vehicle_types: list
        list of vehicle types and number of vehicles for each type.
    bases: list
        list of bases objects.
    charge_curve: pd.DataFrame
        Dataframe containing a charge curve for all vehicles.
    whmi_lookup: pd.DataFrame
        Dataframe containing a watt-hour per mile lookup for all vehicles.
    env_params: dict
        dictionary of all of the constant environment parameters shared across the simulation.
    clock: hive.utils.Clock
        simulation clock shared across the simulation to track simulation time steps.

    Returns
    -------
    veh_fleet: list
        list of all initialized vehicles
    fleet_state: np.ndarray
        matrix that represents the state of the fleet. Used for quick numpy vectorized operations.
    """
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
                        env_params = env_params,
                        vehicle_log = vehicle_log,
                        )

            id += 1

            avg_kwh__mi = np.average(scaled_whmi_lookup['whmi']) / 1000

            veh_fleet.append(veh)

            #TODO: Make this more explicit
            fleet_state_constructor.append((veh.lat, #lat
                                            veh.lon, #lon
                                            1, #active
                                            1, #available
                                            0, #soc
                                            0, #idle_min
                                            veh.MAX_PASSENGERS, #avail_seats
                                            0, #charging
                                            0, #reserve
                                            avg_kwh__mi, #KWH__MI
                                            veh.BATTERY_CAPACITY, #BATTERY_CAPACITY_KWH
                                            VehicleState.IDLE.value, #vehicle_state
                                            ))

    fleet_state = np.array(fleet_state_constructor)

    # write vehicle log header
    if vehicle_log:
        header = veh_fleet[0].LOG_COLUMNS[0]
        for column in veh_fleet[0].LOG_COLUMNS[1:]:
            header = header + "," + column
        vehicle_log.info(header)

    for veh in veh_fleet:
        #Initialize vehicle location to a random base
        base = random.choice(bases)
        veh.fleet_state = fleet_state
        veh.energy_kwh = np.random.uniform(0.2, 1.0) * veh.BATTERY_CAPACITY
        veh.lat = base.LAT
        veh.lon = base.LON
        veh.vehicle_state = VehicleState.IDLE
        veh.base = base

    return veh_fleet, fleet_state
