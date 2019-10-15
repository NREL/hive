import random
import logging
import geopandas as gpd
from shapely.geometry import Point

from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning


class RandomRepositioning(AbstractRepositioning):

    def __init__(self, seed=0):
        self.random = random
        self.random.seed(seed)
        # sending debugger data to the run log for lack of a better destination
        self._log = logging.getLogger("run_log")
        self.fleet = None
        self.fleet_state = None
        self.route_engine = None
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None
        self.bounding_box = None

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock, log):
        # this "log" is the dispatcher's log. we don't want to mess with that, do we?

        self.fleet = fleet
        self.fleet_state = fleet_state
        self.route_engine = route_engine
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
        randomly repositions the agents within the bounds of the simulation
        """

        agents_repositioned = 0

        reposition_vehicles = list(filter(lambda veh: veh.activity == "Idle", self.fleet))

        # get all inactive agents
        for vehicle in reposition_vehicles:
            # generate random points from min/max x/y values until a pair
            # falls within the bounding polygon (operating area) of the scenario

            rand_lon_pos = self.random.uniform(self.minx, self.maxx)
            rand_lat_pos = self.random.uniform(self.miny, self.maxy)
            samples = 1
            while not self.bounding_box.contains(Point(rand_lon_pos, rand_lat_pos)):
                rand_lon_pos = self.random.uniform(self.minx, self.maxx)
                rand_lat_pos = self.random.uniform(self.miny, self.maxy)
                samples = samples + 1
            self._log.debug("Random Repositioning Vehicle {} after sampling {} points".format(vehicle.ID, samples))

            # route vehicle from current position to the randomly generated point
            route = self.route_engine.route(vehicle.lat, vehicle.lon, rand_lat_pos, rand_lon_pos, "Reposition")
            vehicle.cmd_reposition(route['route'])
            agents_repositioned += 1

    def log(self):
        # does nothing. dispatcher-related logging needs some thinking/re-thinking
        pass
