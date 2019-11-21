from __future__ import annotations

from typing import Tuple, Optional

from h3 import h3

from hive.roadnetwork.link import dist_h3, interpolate_between_geoids
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route, Position, RouteStep, ExperiencedRouteSteps
from hive.util.typealiases import GeoId, LinkId
from hive.config.environment import TIME_STEP_S


class HaversineRoadNetwork(RoadNetwork):
    """
    Implements a simple haversine road network where a unique node exists for each unique GeoId in the simulation.
    This assumes a fully connected graph between each node in which the shortest path is the link that connects any
    two nodes. LinkId is specified as a concatenation of the GeoId of its endpoints in which the order is given by
    origin and destination respectively.
    """

    # TODO: Replace speed with more accurate/dynamic estimate.
    _AVG_SPEED = 40  # km/hour

    def _node_ids_from_link_id(self, link_id: LinkId) -> Tuple[GeoId, GeoId]:
        nodes = link_id.split("-")
        a = nodes[0]
        b = nodes[1]
        return a, b

    def route_by_geoid(self, origin: GeoId, destination: GeoId) -> Route:
        link_id = origin + "-" + destination
        link_distance = dist_h3(origin, destination)

        route_time_estimate = link_distance / self._AVG_SPEED  # hr

        h3_line = h3.h3_line(origin, destination)
        route_steps = tuple(RouteStep(link_id, geo_id) for geo_id in h3_line)

        route = Route(route_steps, route_time_estimate, link_distance)

        return route

    def route_by_position(self, origin: Position, destination: Position) -> Route:
        origin_geoid = self.position_to_geoid(origin)
        destination_geoid = self.position_to_geoid(destination)
        return self.route_by_geoid(origin_geoid, destination_geoid)

    def advance_route(self, route: Route) -> Tuple[Optional[Route], ExperiencedRouteSteps]:
        travel_time_s = 0
        travel_distance_km = 0
        route_steps = list()
        # TODO: Replace with recursion to adhere to FP??
        while travel_time_s < TIME_STEP_S and route:
            route, route_step = route.step()
            step_speed = self.get_link_speed(route_step.link_id)

            step_time_s = route_step.DISTANCE / step_speed
            travel_time_s += step_time_s
            travel_distance_km += route_step.DISTANCE

            experienced_route_step = route_step.add_experienced_time(step_time_s)

            route_steps.append(experienced_route_step)

        experienced_route_steps = ExperiencedRouteSteps(tuple(route_steps), travel_time_s, travel_distance_km)

        return route, experienced_route_steps

    def update(self, sim_time: int) -> RoadNetwork:
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the sim time to update the model to
        :return: does not return
        """

        # This particular road network doesn't keep track of network flow so this method does nothing.
        pass

    def get_link_speed(self, link_id: LinkId) -> float:
        """
        gets the current link speed for the provided Position
        :param link_id: the location on the road network
        :return: speed
        """
        return self._AVG_SPEED

    def postition_to_geoid(self, position: Position) -> GeoId:
        """
        does the work to determine the coordinate of this position on the road network
        :param link_id: a position on the road network
        :param resolution: h3 resolution
        :return: an h3 geoid at this position
        """
        node_a_geoid, node_b_geoid = self._node_ids_from_link_id(position.link_id)

        node_c_geoid = interpolate_between_geoids(node_a_geoid, node_b_geoid, position.percent_from_origin)

        return node_c_geoid

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param geoid: an h3 geoid
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def link_id_within_geofence(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param geoid: an h3 geoid
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def link_id_within_simulation(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")
