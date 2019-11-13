from unittest import TestCase, skip

from h3 import h3

from hive.model.base import Base
from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.roadnetwork.position import Position
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route
from hive.roadnetwork.routestep import RouteStep
from hive.simulationstate.simulationstate import SimulationState
from hive.simulationstate.simulationstateops import initial_simulation_state
from hive.util.typealiases import *


class TestSimulationState(TestCase):
    def test_add_request(self):
        req = self.mock_request()
        sim = self.mock_sim()
        sim_with_req = sim.add_request(req)
        self.assertEqual(len(sim.requests), 0, "the original sim object should not have been mutated")

        # todo: request's coordinate is pushed to the centroid of a h3 cell. is this correct?
        #  users might get confused by this and think something is wrong in the sim
        #  instead, we could use a distance test, supported by the native h3 distance check.
        # self.assertEqual(sim.requests[req.id], req, "request contents should be idempotent")

        req_geoid = h3.geo_to_h3(req.origin.lat, req.origin.lon, sim_with_req.sim_h3_resolution)
        at_loc = sim_with_req.r_locations[req_geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 request at this location")
        self.assertEqual(at_loc[0], req.id, "the request's id should be found at it's geoid")

    def test_remove_request(self):
        req = self.mock_request()
        sim = self.mock_sim()
        sim_with_req = sim.add_request(req)
        sim_after_remove = sim_with_req.remove_request(req.id)

        self.assertEqual(len(sim_with_req.requests), 1, "the sim with req added should not have been mutated")
        self.assertEqual(len(sim_after_remove.requests), 0, "the request should have been removed")

        req_geoid = h3.geo_to_h3(req.origin.lat, req.origin.lon, sim_with_req.sim_h3_resolution)
        at_location = sim_after_remove.r_locations[req_geoid]
        self.assertEqual(len(at_location), 0, "the request should have been removed")

    def test_add_vehicle(self):
        veh = self.mock_vehicle()
        sim = self.mock_sim()
        sim_with_veh = sim.add_vehicle(veh)

        self.assertEqual(len(sim.vehicles), 0, "the original sim object should not have been mutated")

        veh_coord = sim.road_network.position_to_coordinate(veh.position)
        veh_geoid = h3.geo_to_h3(veh_coord.lat, veh_coord.lon, sim_with_veh.sim_h3_resolution)
        at_loc = sim_with_veh.v_locations[veh_geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 vehicle at this location")
        self.assertEqual(at_loc[0], veh.id, "the vehicle's id should be found at it's geoid")

    def test_remove_vehicle(self):
        veh = self.mock_vehicle()
        sim = self.mock_sim()
        sim_with_veh = sim.add_vehicle(veh)
        sim_after_remove = sim_with_veh.remove_vehicle(veh.id)

        self.assertEqual(len(sim_with_veh.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_remove.vehicles), 0, "the vehicle should have been removed")

        veh_coord = sim.road_network.position_to_coordinate(veh.position)
        veh_geoid = h3.geo_to_h3(veh_coord.lat, veh_coord.lon, sim_with_veh.sim_h3_resolution)
        at_location = sim_after_remove.v_locations[veh_geoid]
        self.assertEqual(len(at_location), 0, "the vehicle should have been removed")

    def test_pop_vehicle(self):
        veh = self.mock_vehicle()
        sim = self.mock_sim().add_vehicle(veh)
        sim_after_pop, veh_after_pop = sim.pop_vehicle(veh.id)

        self.assertEqual(len(sim.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_pop.vehicles), 0, "the vehicle should have been removed")
        self.assertEqual(veh, veh_after_pop, "should be the same vehicle that gets popped")

    def test_add_station(self):
        self.fail()

    def test_add_base(self):
        self.fail()

    def test_update_road_network(self):
        self.fail()

    def test_board_vehicle(self):
        self.fail()

    def test_vehicle_at_request(self):
        self.fail()

    def test_get_vehicle_geoid(self):
        self.fail()

    def test_vehicle_at_station(self):
        self.fail()

    def test_vehicle_at_base(self):
        self.fail()

    def test_apply_updated_vehicle(self):
        self.fail()

    # mock stuff

    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: Position, destination: Position) -> Route:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            pass

        def coordinate_to_position(self, coordinate: Coordinate) -> Position:
            return coordinate

        def position_to_coordinate(self, position: Position) -> Coordinate:
            return position

        def coordinate_within_geofence(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_geofence(self, position: Position) -> bool:
            return True

        def coordinate_within_simulation(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_simulation(self, position: Position) -> bool:
            return True

    class MockEngine(Engine):
        """
        i haven't made instances of Engine yet. 20191106-rjf
        """

        def route_fuel_cost(self, route: Route) -> KwH:
            return len(route.route)

        def route_step_fuel_cost(self, route_step: RouteStep) -> KwH:
            return 1.0

    def mock_request(self) -> Request:
        return Request.build(
            _id="r1",
            _origin=Coordinate(lat=0.0, lon=0.0),
            _destination=Coordinate(lat=3.0, lon=4.0),
            _departure_time=28800,
            _cancel_time=29400,
            _passengers=2
        )

    def mock_vehicle(self) -> Vehicle:
        return Vehicle(
            "m1",
            self.MockEngine(),
            Battery.build("battery", 100),
            Coordinate(0, 0)
        )

    def mock_station(self) -> Station:
        return Station("s1", Coordinate(10, 0))

    def mock_base(self) -> Base:
        return Base("b1", Coordinate(3, 3))

    def mock_sim(self) -> SimulationState:
        sim, failures = initial_simulation_state(self.MockRoadNetwork())
        assert len(failures) == 0, f"default sim used for tests had failures:\n {failures}"
        return sim
