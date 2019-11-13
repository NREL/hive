import copy
from typing import cast
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
        req = SimulationStateTestAssets.mock_request()
        sim = SimulationStateTestAssets.mock_empty_sim()
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
        req = SimulationStateTestAssets.mock_request()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_req = sim.add_request(req)
        sim_after_remove = sim_with_req.remove_request(req.id)

        self.assertEqual(len(sim_with_req.requests), 1, "the sim with req added should not have been mutated")
        self.assertEqual(len(sim_after_remove.requests), 0, "the request should have been removed")

        req_geoid = h3.geo_to_h3(req.origin.lat, req.origin.lon, sim_with_req.sim_h3_resolution)
        at_location = sim_after_remove.r_locations[req_geoid]
        self.assertEqual(len(at_location), 0, "the request should have been removed")

    def test_add_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_veh = sim.add_vehicle(veh)

        self.assertEqual(len(sim.vehicles), 0, "the original sim object should not have been mutated")
        self.assertEqual(sim_with_veh.vehicles[veh.id], veh, "the vehicle should not have been mutated")

        veh_coord = sim.road_network.position_to_coordinate(veh.position)
        veh_geoid = h3.geo_to_h3(veh_coord.lat, veh_coord.lon, sim_with_veh.sim_h3_resolution)
        at_loc = sim_with_veh.v_locations[veh_geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 vehicle at this location")
        self.assertEqual(at_loc[0], veh.id, "the vehicle's id should be found at it's geoid")

    def test_remove_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_veh = sim.add_vehicle(veh)
        sim_after_remove = sim_with_veh.remove_vehicle(veh.id)

        self.assertEqual(len(sim_with_veh.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_remove.vehicles), 0, "the vehicle should have been removed")

        veh_coord = sim.road_network.position_to_coordinate(veh.position)
        veh_geoid = h3.geo_to_h3(veh_coord.lat, veh_coord.lon, sim_with_veh.sim_h3_resolution)
        at_location = sim_after_remove.v_locations[veh_geoid]
        self.assertEqual(len(at_location), 0, "the vehicle should have been removed")

    def test_pop_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh)
        sim_after_pop, veh_after_pop = sim.pop_vehicle(veh.id)

        self.assertEqual(len(sim.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_pop.vehicles), 0, "the vehicle should have been removed")
        self.assertEqual(veh, veh_after_pop, "should be the same vehicle that gets popped")

    def test_add_base(self):
        base = SimulationStateTestAssets.mock_base()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_base = sim.add_base(base)

        self.assertEqual(len(sim_after_base.bases), 1, "the sim should have one base added")
        self.assertEqual(sim_after_base.bases[base.id], base, "the base should not have been mutated")

        s_geoid = h3.geo_to_h3(base.coordinate.lat, base.coordinate.lon, sim_after_base.sim_h3_resolution)
        at_loc = sim_after_base.s_locations[s_geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 base at this location")
        self.assertEqual(at_loc[0], base.id, "the base's id should be found at it's geoid")

    def test_add_base(self):
        base = SimulationStateTestAssets.mock_base()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_base = sim.add_base(base)

        self.assertEqual(len(sim_after_base.bases), 1, "the sim should have one base added")
        self.assertEqual(sim_after_base.bases[base.id], base, "the base should not have been mutated")

        b_geoid = h3.geo_to_h3(base.coordinate.lat, base.coordinate.lon, sim_after_base.sim_h3_resolution)
        at_loc = sim_after_base.b_locations[b_geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 base at this location")
        self.assertEqual(at_loc[0], base.id, "the base's id should be found at it's geoid")

    def test_update_road_network(self):
        sim = SimulationStateTestAssets.mock_empty_sim()
        update_time_argument = 1999
        updated_sim = sim.update_road_network(update_time_argument)
        updated_road_network = cast(SimulationStateTestAssets.MockRoadNetwork, updated_sim.road_network)
        self.assertEqual(updated_road_network.updated_to_time_step, update_time_argument)

    def test_vehicle_at_request(self):
        """
        invariant: mock vehicle and request are at same location
        """
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(90, 90))
        req = SimulationStateTestAssets.mock_request(origin=Coordinate(90, 90))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertTrue(result, "the vehicle should be at the request")

    def test_vehicle_not_at_request(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(0, 0))
        req = SimulationStateTestAssets.mock_request(origin=Coordinate(45, 45))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertFalse(result, "the vehicle should not be at the request")

    def test_vehicle_at_station(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(45, 45))
        sta = SimulationStateTestAssets.mock_station(coordinate=Coordinate(45, 45))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertTrue(result, "the vehicle should be at the station")

    def test_vehicle_not_at_station(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(0, 0))
        sta = SimulationStateTestAssets.mock_station(coordinate=Coordinate(45, 45))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertFalse(result, "the vehicle should not be at the station")

    def test_vehicle_at_base(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(45, 45))
        base = SimulationStateTestAssets.mock_base(coordinate=Coordinate(45, 45))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertTrue(result, "the vehicle should be at the base")

    def test_vehicle_not_at_base(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(0, 0))
        base = SimulationStateTestAssets.mock_base(coordinate=Coordinate(45, 45))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertFalse(result, "the vehicle should not be at the base")

    @skip
    def test_get_vehicle_geoid(self):
        """
        maybe skip testing this functionality? seems kinda like testing h3 itself
        :return:
        """
        pass

    def test_board_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(51, 50))
        req = SimulationStateTestAssets.mock_request(origin=Coordinate(51, 50), passengers=2)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)

        sim_boarded = sim.board_vehicle(req.id, veh.id)

        # check that both passengers boarded correctly
        self.assertIn(req.passengers[0], sim_boarded.vehicles[veh.id].passengers,
                         f"passenger {req.passengers[0].id} didn't board")
        self.assertIn(req.passengers[1], sim_boarded.vehicles[veh.id].passengers,
                      f"passenger {req.passengers[1].id} didn't board")

    def test_apply_updated_vehicle(self):
        self.fail()


class SimulationStateTestAssets:
    class MockRoadNetwork(RoadNetwork):
        updated_to_time_step: int = 0

        def route(self, origin: Position, destination: Position) -> Route:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            updated = copy.deepcopy(self)
            updated.updated_to_time_step = sim_time
            return updated

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

    @classmethod
    def mock_request(cls,
                     origin: Coordinate = Coordinate(lat=0.0, lon=0.0),
                     destination: Coordinate = Coordinate(lat=3.0, lon=4.0),
                     passengers: int = 2) -> Request:
        return Request.build(
            _id="r1",
            _origin=origin,
            _destination=destination,
            _departure_time=28800,
            _cancel_time=29400,
            _passengers=passengers
        )

    @classmethod
    def mock_vehicle(cls, position: Position = Coordinate(0, 0)) -> Vehicle:
        return Vehicle(
            "m1",
            cls.MockEngine(),
            Battery.build("battery", 100),
            position
        )

    @classmethod
    def mock_station(cls, coordinate: Coordinate = Coordinate(10, 0)) -> Station:
        return Station("s1", coordinate)

    @classmethod
    def mock_base(cls, coordinate: Coordinate = Coordinate(3, 3)) -> Base:
        return Base("b1", coordinate)

    @classmethod
    def mock_empty_sim(cls) -> SimulationState:
        sim, failures = initial_simulation_state(cls.MockRoadNetwork())
        assert len(failures) == 0, f"default sim used for tests had failures:\n {failures}"
        return sim
