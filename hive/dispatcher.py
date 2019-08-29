"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and station/base selection.
"""

import datetime
import numpy as np

from hive import tripenergy as nrg
from hive import charging as chrg
from hive import helpers as hlp
from hive.units import METERS_TO_MILES

class Dispatcher:
    """
    The Dispatcher object is responsible for coordinating the actions of the fleet.

    Parameters
    ----------
    fleet: list
        list of all vehicles in the fleet.
    fleet_state: np.ndarray
        matrix that represents the state of the fleet. Used for quick numpy vectorized operations.
    stations: list
        list of all charging stations.
    bases: list
        list of all bases
    env_params: dict
        dictionary of all of the constant environment parameters shared across the simulation.
    clock: hive.utils.Clock
        simulation clock shared across the simulation to track simulation time steps.
    """


    def __init__(
                self,
                fleet,
                fleet_state,
                stations,
                bases,
                env_params,
                clock,
                ):

        self.ID = 0

        self._fleet = fleet
        self._fleet_state = fleet_state
        for veh in self._fleet:
            veh.fleet_state = fleet_state

        self._clock = clock

        self._stations = stations
        self._bases = bases

        self.history = []
        self._dropped_requests = 0

        self._ENV = env_params


    def _log(self):
        """
        Function stores the partial state of the object at each time step.
        """

        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()

        self.history.append({
                        'sim_time': self._clock.now,
                        'active_vehicles': active_vehicles,
                        'dropped_requests': self._dropped_requests,
                        })


    def _find_closest_plug(self, vehicle, type='station'):
        """
        Function takes hive.vehicle.Vehicle object and returns the FuelStation
        nearest Vehicle with at least one available plug. The "type" argument
        accepts either 'station' or 'base', informing the search space.

        Parameters
        ----------
        vehicle: hive.vehicle.Vehicle
            vehicle to which the closest plug is relative to.
        type: str
            string to indicate which type of plug is being searched for.

        Returns
        -------
        nearest: hive.stations.FuelStation
            the station or bases that is the closest to the vehicle
        """
        #IDEA: Store stations in a geospatial index to eliminate exhaustive search. -NR
        INF = 1000000000

        if type == 'station':
            network = self._stations
        elif type == 'base':
            network = self._bases

        def recursive_search(search_space):
            if len(search_space) < 1:
                raise NotImplementedError("""No plugs are available on the
                    entire network.""")

            dist_to_nearest = INF
            for station in search_space:
                dist_mi = hlp.estimate_vmt_2D(vehicle.x,
                                               vehicle.y,
                                               station.X,
                                               station.Y,
                                               scaling_factor = vehicle.ENV['RN_SCALING_FACTOR'])
                if dist_mi < dist_to_nearest:
                    dist_to_nearest = dist_mi
                    nearest = station
            if nearest.avail_plugs < 1:
                search_space = [s for s in search_space if s.ID != nearest.ID]
                nearest = recursive_search(search_space)

            return nearest

        nearest = recursive_search(network)

        return nearest

    def _get_n_best_vehicles(self, request, n):
        """
        Function takes a single request and returns the n best vehicles with respect
        to that request.

        Parameters
        ----------
        request: NamedTuple
            request named tuple to match n vehicles to.
        n: int
            how many vehicles to return.

        Returns
        -------
        best_vehs_ids: np.ndarray
            array of the best n vehicle ids in sorted order from best -> worst.

        """
        fleet_state = self._fleet_state
        point = np.array([(request.pickup_x, request.pickup_y)])
        dist = np.linalg.norm(fleet_state[:, :2] - point, axis=1) * METERS_TO_MILES
        best_vehs_idx = np.argsort(dist)
        dist_mask = dist < self._ENV['MAX_DISPATCH_MILES']

        available_col = self._ENV['FLEET_STATE_IDX']['available']
        available_mask = (fleet_state[:,available_col] == 1)

        soc_col = self._ENV['FLEET_STATE_IDX']['soc']
        KWH__MI_col = self._ENV['FLEET_STATE_IDX']['KWH__MI']
        BATTERY_CAPACITY_KWH_col = self._ENV['FLEET_STATE_IDX']['BATTERY_CAPACITY_KWH']
        min_soc_mask = (fleet_state[:, soc_col] \
            - ((dist + request.distance_miles) * fleet_state[:, KWH__MI_col]) \
            /fleet_state[:, BATTERY_CAPACITY_KWH_col] > self._ENV['MIN_ALLOWED_SOC'])

        avail_seats_col = self._ENV['FLEET_STATE_IDX']['avail_seats']
        avail_seats_mask = fleet_state[:, avail_seats_col] >= request.passengers

        mask = dist_mask & available_mask & min_soc_mask & avail_seats_mask
        best_vehs_ids = best_vehs_idx[mask[best_vehs_idx]][:n]
        return best_vehs_ids

    def _dispatch_vehicles(self, requests):
        """
        Function coordinates vehicle dispatch actions for a single timestep given
        one or more requests.

        Parameters
        ----------
        requests: list
            list of requests that occur in a single time step.
        """
        self._dropped_requests = 0
        for request in requests.itertuples():
            best_vehicle = self._get_n_best_vehicles(request, n=1)
            if len(best_vehicle) < 1:
                self._dropped_requests += 1
            else:
                vehid = best_vehicle[0]
                veh = self._fleet[vehid]
                veh.cmd_make_trip(
                        request.pickup_x,
                        request.pickup_y,
                        request.dropoff_x,
                        request.dropoff_y,
                        passengers = request.passengers,
                        trip_dist_mi=request.distance_miles,
                        trip_time_s=request.seconds,
                        # route=request.route_utm)
                        )

    def _charge_vehicles(self):
        """
        Function commands vehicles to charge if their SOC dips beneath the
        LOWER_SOC_THRESH_STATION environment variable.
        """
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']
        available_col = self._ENV['FLEET_STATE_IDX']['available']
        active_col = self._ENV['FLEET_STATE_IDX']['active']
        mask = (self._fleet_state[:, soc_col] < self._ENV['LOWER_SOC_THRESH_STATION']) \
            & (self._fleet_state[:,available_col] == 1) & (self._fleet_state[:, active_col] == 1)
        veh_ids = np.argwhere(mask)

        for veh_id in veh_ids:
            vehicle = self._fleet[veh_id[0]]
            station = self._find_closest_plug(vehicle)
            vehicle.cmd_charge(station)

    def _check_idle_vehicles(self):
        """
        Function checks for any vehicles that have been idling for longer than
        MAX_ALLOWABLE_IDLE_MINUTES and commands those vehicles to return to their
        respective base.
        """
        idle_min_col = self._ENV['FLEET_STATE_IDX']['idle_min']
        idle_mask = self._fleet_state[:, idle_min_col] >= self._ENV['MAX_ALLOWABLE_IDLE_MINUTES']
        veh_ids = np.argwhere(idle_mask)

        for veh_id in veh_ids:
            vehicle = self._fleet[veh_id[0]]
            base = self._find_closest_plug(vehicle, type='base')
            vehicle.cmd_return_to_base(base)

    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step. Function takes
        a list of requests and coordinates vehicle actions for that step.

        Parameters
        ----------
        requests: list
            one or many requests to distribute to the fleet.
        """
        self._charge_vehicles()
        self._dispatch_vehicles(requests)
        self._check_idle_vehicles()
        self._log()
