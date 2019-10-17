"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and station/base selection.
"""

import numpy as np

from hive import helpers as hlp
from hive import units
from hive.utils import generate_csv_row
from hive.dispatcher.assignment import AbstractServicing
from hive.vehiclestate import VehicleState

class GreedyAssignment(AbstractServicing):
    """
    Uses a greedy strategy to create agent plans

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
                demand,
                env_params,
                route_engine,
                clock,
                log,
                ):
        super().__init__()


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
                dist_mi = hlp.estimate_vmt_latlon(vehicle.lat,
                                               vehicle.lon,
                                               station.LAT,
                                               station.LON,
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
        point = np.array([request.pickup_lat, request.pickup_lon])
        lat_col = self._ENV['FLEET_STATE_IDX']['lat']
        lon_col = self._ENV['FLEET_STATE_IDX']['lon']
        dist = hlp.haversine_np(
                        fleet_state[:, lat_col].astype(np.float64),
                        fleet_state[:, lon_col].astype(np.float64),
                        point[0],
                        point[1],
                        )

        best_vehs_idx = np.argsort(dist)
        dist_mask = dist < self._ENV['MAX_DISPATCH_MILES']

        available_col = self._ENV['FLEET_STATE_IDX']['available']
        available_mask = (fleet_state[:,available_col] == 1)

        #TODO: Update this to include energy required to dispatch and get to
        #      nearest charger.
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
        self._total_requests = len(requests)
        self._wait_time_min = 0
        for request in requests.itertuples():
            best_vehicle = self._get_n_best_vehicles(request, n=1)
            if len(best_vehicle) < 1:
                self._dropped_requests += 1
            else:
                vehid = best_vehicle[0]
                veh = self._fleet[vehid]
                disp_route_summary = self._route_engine.route(
                                        veh.lat,
                                        veh.lon,
                                        request.pickup_lat,
                                        request.pickup_lon,
                                        vehicle_state=VehicleState.DISPATCH_TRIP)
                disp_route = disp_route_summary['route']
                self._wait_time_min += disp_route_summary['trip_time_s'] * units.SECONDS_TO_MINUTES

                if hasattr(request, 'route'):
                    trip_route = request.route
                else:
                    trip_route_summary = self._route_engine.route(
                                            request.pickup_lat,
                                            request.pickup_lon,
                                            request.dropoff_lat,
                                            request.dropoff_lon,
                                            vehicle_state=VehicleState.SERVING_TRIP,
                                            trip_dist_mi=request.distance_miles,
                                            trip_time_s=request.seconds,
                                            )
                    trip_route = trip_route_summary['route']

                del disp_route[-1]
                route = disp_route + trip_route

                veh.cmd_make_trip(
                        route = route,
                        passengers = request.passengers,
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
            route_summary = self._route_engine.route(vehicle.lat, vehicle.lon,
                                                     station.LAT, station.LON,
                                                     VehicleState.DISPATCH_STATION)
            route = route_summary['route']
            vehicle.cmd_charge(station, route)

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
            route_summary = self._route_engine.route(vehicle.lat, vehicle.lon,
                                                     base.LAT, base.LON,
                                                     VehicleState.DISPATCH_BASE)
            route = route_summary['route']
            vehicle.cmd_return_to_base(base, route)

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
