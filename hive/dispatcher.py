"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and DCFC station/depot selection.
"""

import datetime
from haversine import haversine

from hive import tripenergy as nrg
from hive import charging as chrg

class Dispatcher:
    """
    Base class for dispatcher.

    Inputs
    ------
    requests : list
        List of requests for simulation timestep

    Outputs
    -------

    """
    _STATS = [
        'failure_active_max_dispatch',
        'failure_active_time',
        'failure_active_battery',
        'failure_inactive_time',
        'failure_inactive_battery',
    ]

    def __init__(self, fleet, stations, depots):
        self._fleet = fleet
        self._stations = stations
        self._depots = depots

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def _check_active_viability(self, veh, request):
        """
        Checks if active vehicle can fulfill request w/o violating several
        constraints. Function requires a hive.Vehicle object and a trip request
        Function returns a boolean indicating the ability of the vehicle to service
        the request and the updated failure log. This function also sends vehicles
        exceeding the MAX_WAIT_TIME_MINUTES constraint to a depot for charging.
        """

        # Unpack request
        pickup_time = request[3]
        dropoff_time = request[4]
        trip_dist = request[5]
        pickup_lat = request[6]
        pickup_lon = request[7]

        assert veh.active==True, "Vehicle is not active!"

        # Check 1 - Max Dispatch Constraint Not Violated
        disp_dist = haversine((veh.avail_lat, veh.avail_lon),
                                (pickup_lat, pickup_lon), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
        if disp_dist > veh.ENV['MAX_DISPATCH_MILES']:
            self.stats['failure_active_max_dispatch']+=1
            return False

        # Check 2 - Time Constraint Not Violated
        disp_time_s = disp_dist/veh.ENV['DISPATCH_MPH'] * 3600
        if veh.avail_time + datetime.timedelta(seconds=disp_time_s) > pickup_time:
            self.stats['failure_active_time']+=1
            return False

        # Check 3 - Battery Constraint Not Violated
        disp_energy = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh.WH_PER_MILE_LOOKUP)
        trip_time_s = (dropoff_time - pickup_time).total_seconds()
        trip_energy = nrg.calc_trip_kwh(trip_dist, trip_time_s, veh.WH_PER_MILE_LOOKUP)
        total_request_energy = disp_energy + trip_energy
        hyp_energy_remaining = veh.energy_remaining - total_request_energy
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY
        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            self.stats['failure_active_battery']+=1
            return False

        # Check 4 - Vehicle Should Not Have Been Active For Request
        idle_time_s = ((pickup_time - datetime.timedelta(seconds=disp_time_s)) \
        - veh.avail_time).total_seconds()
        idle_time_min = idle_time_s / 60
        if idle_time_min > veh.ENV['MAX_WAIT_TIME_MINUTES']:
            depot = self._find_nearest_plug(veh)
            veh.return_to_depot(depot)
            depot.avail_plugs -= 1
            return False

        return True

    def _check_inactive_viability(self, veh, request):
        """
        Checks if inactive vehicle can fulfill request w/o violating several
        constraints. Function requires a hive.Vehicle object and a trip request.
        Function returns a boolean indicating the ability
        of the vehicle to service the request.
        """

        # Unpack request
        pickup_time = request[3]
        dropoff_time = request[4]
        trip_dist = request[5]
        pickup_lat = request[6]
        pickup_lon = request[7]

        assert veh.active!=True, "Vehicle is active!"

        # Check 1 - Time Constraint Not Violated
        disp_dist = haversine((veh.avail_lat, veh.avail_lon),
                                (pickup_lat, pickup_lon), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
        disp_time_s = disp_dist/veh.ENV['DISPATCH_MPH'] * 3600
        if (veh.avail_time!=0) and (veh.avail_time + datetime.timedelta(seconds=disp_time_s) > pickup_time):
            self.stats['failure_inactive_time']+=1
            return False
        # Check 2 - Battery Constraint Not Violated
        disp_energy = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh.WH_PER_MILE_LOOKUP)
        trip_time_s = (dropoff_time - pickup_time).total_seconds()
        trip_energy = nrg.calc_trip_kwh(trip_dist, trip_time_s, veh.WH_PER_MILE_LOOKUP)
        total_request_energy = disp_energy + trip_energy

        for depot in self._depots:
            if veh.avail_lat == depot.LAT and veh.avail_lon == depot.LON:
                charge_type = depot.PLUG_TYPE
                charge_power = depot.PLUG_POWER
                break

        #TODO: Refactor charging.py for single function that accepts charge_type,
        ##charge power, time, and considers max_acceptance, returning soc_f
        ###then: hyp_energy_remaining = (self.battery_capacity * soc_f) - total_energy
        hyp_energy_remaining = 0

        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY
        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            self.stats['failure_inactive_battery']+=1
            return False

        return True

    def _find_nearest_plug(self, veh):
        """
        Function takes hive.vehicle.Vehicle object and returns the FuelStation nearest
        Vehicle with at least one available plug.
        """
        #IDEA: Store stations in a geospatial index to elminate exhaustive search. -NR
        nearest, dist_to_nearest = None, None
        for station in self._stations:
            if station.avail_plugs != 0:
                dist = haversine((veh.avail_lat, veh.avail_lon),
                                (station.LAT, station.LON), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
                if (nearest == None) and (dist_to_nearest == None):
                    nearest = station
                    dist_to_nearest = dist
                else:
                    if dist < dist_to_nearest:
                        nearest = station
                        dist_to_nearest = dist

        return nearest

    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step.

        Inputs
        ------
        requests - one or many requests to distribute to the fleet.
        """
        #Catch single requests.
        if type(requests) != type(list()):
            requests = [requests]

        for req in requests:
            req_filled = False #default
            for veh in self._fleet:
                # Check active vehicles in fleet
                if veh.active:
                    viable = self._check_active_viability(veh, req)
                    if viable:
                        veh.make_trip(req)
                        self._fleet.remove(veh) #pop veh from queue
                        self._fleet.append(veh) #append veh to end of queue
                        req_filled = True
                        break
            if not req_filled:
                #TODO: Remove break when check_inactive_viability() is completed.
                break
                for veh in self._fleet:
                    # Check inactive (depot) vehicles in fleet
                    if not veh.active:
                        viable = self._check_inactive_viability(veh, req)
                        if viable:
                            veh.make_trip(req)
                            self._fleet.remove(veh) #pop veh from queue
                            self._fleet.append(veh) #append veh to end of queue
                            req_filled = True
                            break
            if not req_filled:
                pass
                #TODO: Write failure log to CSV
