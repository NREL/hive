"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and station/base selection.
"""

import numpy as np

from hive import helpers as hlp
from hive import units
from hive.utils import generate_csv_row
from hive.dispatcher.active_charging import AbstractCharging
from hive.vehiclestate import VehicleState

class BasicCharging(AbstractCharging):
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
                ):
        super().__init__(
                fleet,
                fleet_state,
                stations,
                bases,
                demand,
                env_params,
                route_engine,
                clock,
                )


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


    def charge(self):
        """
        process_requests is called for each simulation time step. Function takes
        a list of requests and coordinates vehicle actions for that step.

        Parameters
        ----------
        requests: list
            one or many requests to distribute to the fleet.
        """
        self._charge_vehicles()

    def log(self):
        pass
