"""
Functions for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and DCFC station/depot selection.
"""

import datetime
from haversine import haversine

from hive import tripenergy as nrg
from hive import charging as chrg


def check_active_viability(veh, request, depots, failure_log):
    """
    Checks if active vehicle can fulfill request w/o violating several
    constraints. Function requires a hive.Vehicle object, trip request, list of
    depots (hive.stations.FuelStation objects), and a failure log dictionary.
    Function returns a boolean indicating the ability of the vehicle to service
    the request and the updated failure log. This function also sends vehicles
    exceeding the MAX_WAIT_TIME_MINUTES constraint to a depot for charging.
    """

    #IDEA: Move global constants to the main.csv/VEH.csv file. For variables
    #that change over the simulation, pass to this function via an input dict. -NR

    # Unpack request
    pickup_time = request[3]
    dropoff_time = request[4]
    trip_dist = request[5]
    pickup_lat = request[6]
    pickup_lon = request[7]

    assert veh.active==True, "Vehicle is not active!"

    # Check 1 - Max Dispatch Constraint Not Violated

    #@NR-Does it make sense to have these env variables be attrs of each veh object?
    ##these are the same regardless of the vehicle...
    disp_dist = haversine((veh.avail_lat, veh.avail_lon), (pickup_lat, pickup_lon), unit='mi') * veh._ENV['RN_SCALING_FACTOR']
    if disp_dist > veh._ENV['MAX_DISPATCH_MILES']:
        failure_log['active_max_dispatch']+=1
        return False, failure_log

    # Check 2 - Time Constraint Not Violated
    disp_time_s = disp_dist/veh._ENV['DISPATCH_MPH'] * 3600
    if veh.avail_time + datetime.timedelta(seconds=disp_time_s) > pickup_time:
        failure_log['active_time']+=1
        return False, failure_log

    # Check 3 - Battery Constraint Not Violated
    disp_energy = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh._wh_per_mile_lookup)
    trip_time_s = (dropoff_time - pickup_time).total_seconds()
    trip_energy = nrg.calc_trip_kwh(trip_dist, trip_time_s, veh._wh_per_mile_lookup)
    total_request_energy = disp_energy + trip_energy
    hyp_energy_remaining = veh.energy_remaining - total_request_energy
    hyp_soc = hyp_energy_remaining / veh._battery_capacity
    if hyp_soc < veh._ENV['MIN_ALLOWED_SOC']:
        failure_log['active_battery']+=1
        return False, failure_log

    # Check 4 - Vehicle Should Not Have Been Active For Request
    idle_time_s = ((pickup_time - datetime.timedelta(seconds=disp_time_s)) - veh.avail_time).total_seconds()
    idle_time_min = idle_time_s / 60
    if idle_time_min > veh._ENV['MAX_WAIT_TIME_MINUTES']:
        depot = find_nearest_plug(veh, depots)
        veh.return_to_depot(depot)
        depot.avail_plugs -= 1
        return False, failure_log

    return True, failure_log

def check_inactive_viability(veh, request, depots, failure_log):
    """
    Checks if inactive vehicle can fulfill request w/o violating several
    constraints. Function requires a hive.Vehicle object, trip request, and
    failure log dictionary. Function returns a boolean indicating the ability
    of the vehicle to service the request and the updated failure log.
    """

    # Unpack request
    pickup_time = request[3]
    dropoff_time = request[4]
    trip_dist = request[5]
    pickup_lat = request[6]
    pickup_lon = request[7]

    assert veh.active!=True, "Vehicle is active!"

    # Check 1 - Time Constraint Not Violated
    disp_dist = haversine((veh.avail_lat, veh.avail_lon), (pickup_lat, pickup_lon), unit='mi') * veh._ENV['RN_SCALING_FACTOR']
    disp_time_s = disp_dist/veh._ENV['DISPATCH_MPH'] * 3600
    if (veh.avail_time!=0) and (veh.avail_time + datetime.timedelta(seconds=disp_time_s) > pickup_time):
        failure_log['inactive_time']+=1
        return False, failure_log

    # Check 2 - Battery Constraint Not Violated
    disp_energy = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh._wh_per_mile_lookup)
    trip_time_s = (dropoff_time - pickup_time).total_seconds()
    trip_energy = nrg.calc_trip_kwh(trip_dist, trip_time_s, veh._wh_per_mile_lookup)
    total_request_energy = disp_energy + trip_energy

    for depot in depots:
        if veh.avail_lat == depot.lat and veh.avail_lon == depot.lon:
            charge_type = depot.type
            charge_power = depot.plug_power
            break

    #TODO: Refactor charging.py for single function that accepts charge_type,
    ##charge power, time, and considers max_acceptance, returning soc_f
    ###then: hyp_energy_remaining = (self.battery_capacity * soc_f) - total_energy

    hyp_soc = hyp_energy_remaining / self._battery_capacity
    if hyp_soc < self._ENV['MIN_ALLOWED_SOC']:
        failure_log['inactive_battery']+=1
        return False, failure_log

    return True

def find_nearest_plug(veh, fuel_stations):
    """
    Function takes hive.vehicle.Vehicle object and list of
    hive.station.FuelStation objects and returns the FuelStation nearest
    Vehicle with at least one available plug. Note this function can be used
    to locate the nearest station or depot depending on the provided list.
    """
    nearest, dist_to_nearest = None, None
    for station in fuel_stations:
        if station.avail_plugs != 0:
            dist = haversine((veh.avail_lat, veh.avail_lon), (station.lat, station.lon), unit='mi') * veh._ENV['RN_SCALING_FACTOR']
            if (nearest == None) and (dist_to_nearest == None):
                nearest = station
                dist_to_nearest = dist
            else:
                if dist < dist_to_nearest:
                    nearest = station
                    dist_to_nearest = dist

    return nearest
