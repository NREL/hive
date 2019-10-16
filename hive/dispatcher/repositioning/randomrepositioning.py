import random
import logging
import geopandas as gpd
from shapely.geometry import Point

from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning
from hive.vehiclestate import VehicleState


class RandomRepositioning(AbstractRepositioning):

    def __init__(self, seed=0):
        self.random = random
        self.random.seed(seed)
        # sending debugger data to the run log for lack of a better destination
        self._log = logging.getLogger("run_log")
        self.fleet = None
        self.fleet_state = None
        self.route_engine = None
        self.clock = None
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None
        self.bounding_box = None
        self.agents_repositioned = 0
        self.random_locations_sampled = 0

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock, log):
        # this "log" is the dispatcher's log. we don't want to mess with that, do we?

        self.fleet = fleet
        self.fleet_state = fleet_state
        self.route_engine = route_engine
        self.clock = clock
        # invariant: should be a single polygon in the provided operating area file
        operating_area = gpd.read_file(env_params['operating_area_file_path'])
        self.bounding_box = operating_area.geometry[0]
        self.minx = float(operating_area.bounds['minx'])
        self.miny = float(operating_area.bounds['miny'])
        self.maxx = float(operating_area.bounds['maxx'])
        self.maxy = float(operating_area.bounds['maxy'])

        # we haven't set up HIVE for repositioning logging
        # write repositioning log header
        # if log:
        #     header = self.LOG_COLUMNS[0]
        #     for column in self.LOG_COLUMNS[1:]:
        #         header = header + "," + column
        #     self.logger.info(header)

    def reposition_agents(self):
        """
        randomly repositions Idle agents within the bounds of the simulation
        """

        agents_repositioned = 0
        random_locations_sampled = 0

        # expensive O(n) filter of all vehicles for "Idle" state
        reposition_vehicles = list(filter(lambda veh: veh.vehicle_state == VehicleState.IDLE, self.fleet))

        # get all inactive agents
        for vehicle in reposition_vehicles:
            # generate random points from min/max x/y values until a pair
            # falls within the bounding polygon (operating area) of the scenario

            rand_lon_pos = self.random.uniform(self.minx, self.maxx)
            rand_lat_pos = self.random.uniform(self.miny, self.maxy)
            random_locations_sampled = random_locations_sampled + 1
            while not self.bounding_box.contains(Point(rand_lon_pos, rand_lat_pos)):
                rand_lon_pos = self.random.uniform(self.minx, self.maxx)
                rand_lat_pos = self.random.uniform(self.miny, self.maxy)
                random_locations_sampled = random_locations_sampled + 1

            # route vehicle from current position to the randomly generated point
            route = self.route_engine.route(vehicle.lat, vehicle.lon, rand_lat_pos, rand_lon_pos, "Reposition")
            vehicle.cmd_reposition(route['route'])
            agents_repositioned += 1

        self.agents_repositioned = self.agents_repositioned + agents_repositioned
        self.random_locations_sampled = self.random_locations_sampled + random_locations_sampled

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug(
                "Random Repositioning finished at time step {} for {} agents".format(self.clock.get_time(),
                                                                                     agents_repositioned))

    def log(self):
        if self._log.isEnabledFor(logging.DEBUG):
            avg_samples = float(self.random_locations_sampled) / float(self.agents_repositioned)
            msg = "Random Repositioning avg location samples: {0:.2f}".format(avg_samples)
            self._log.debug(msg)
        # no real logging implemented yet for Repositioning modules
        pass
