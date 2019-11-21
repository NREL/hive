import copy
from typing import cast
from unittest import TestCase, skip

from h3 import h3

from hive.model.base import Base
from hive.model.energy.energysource import EnergySource
from hive.model.coordinate import Coordinate
from hive.model.energy.powertrain import Powertrain
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle

from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route
from hive.roadnetwork.link import Link
from hive.simulationstate.simulationstate import SimulationState
from hive.simulationstate.simulationstateops import initial_simulation_state
from hive.util.typealiases import *


class TestSimulationState(TestCase):

    def test_add_request(self):
        req = SimulationStateTestAssets.mock_request()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_req = sim.add_request(req)
        self.assertEqual(len(sim.requests), 0, "the original sim object should not have been mutated")
        self.assertEqual(sim_with_req.requests[req.id], req, "request contents should be idempotent")

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

        self.assertNotIn(req.o_geoid, sim_after_remove.r_locations, "there should be no key for this geoid")

    def test_remove_request_multiple_at_loc(self):
        """
        confirms that we didn't remove other requests at the same location
        """
        req1 = SimulationStateTestAssets.mock_request(request_id="1")
        req2 = SimulationStateTestAssets.mock_request(request_id="2")
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_reqs = sim.add_request(req1).add_request(req2)
        sim_remove_req1 = sim_with_reqs.remove_request(req1.id)

        self.assertIn(req2.o_geoid,
                      sim_remove_req1.r_locations,
                      "geoid related to both reqs should still exist")
        self.assertIn(req2.id,
                      sim_remove_req1.r_locations[req2.o_geoid],
                      "req2.id should still be found in r_locations")

    def test_add_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_veh = sim.add_vehicle(veh)

        self.assertEqual(len(sim.vehicles), 0, "the original sim object should not have been mutated")
        self.assertEqual(sim_with_veh.vehicles[veh.id], veh, "the vehicle should not have been mutated")

        at_loc = sim_with_veh.v_locations[veh.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 vehicle at this location")
        self.assertEqual(at_loc[0], veh.id, "the vehicle's id should be found at it's geoid")

    def test_update_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim()
        old_geoid = veh.geoid
        sim_before_update = sim.add_vehicle(veh)

        # modify some values on the vehicle
        new_soc_lower_limit = 0.5
        new_pos = Coordinate(20, 20)
        new_geoid = h3.geo_to_h3(new_pos.lat, new_pos.lon, sim_before_update.sim_h3_resolution)
        updated_vehicle = veh._replace(geoid=new_geoid,
                                       position=new_pos,
                                       soc_lower_limit=new_soc_lower_limit)

        sim_after_update = sim_before_update.modify_vehicle(updated_vehicle)

        # confirm sim reflects changes to vehicle
        self.assertEqual(sim_after_update.vehicles[veh.id].soc_lower_limit, new_soc_lower_limit)
        self.assertIn(veh.id,
                      sim_after_update.v_locations[new_geoid],
                      "new vehicle geoid was not updated correctly")
        self.assertNotIn(veh.geoid,
                         sim_after_update.v_locations,
                         "old vehicle geoid was not updated correctly")

    def test_remove_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_veh = sim.add_vehicle(veh)
        sim_after_remove = sim_with_veh.remove_vehicle(veh.id)

        self.assertEqual(len(sim_with_veh.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_remove.vehicles), 0, "the vehicle should have been removed")

        self.assertNotIn(veh.geoid, sim_after_remove.v_locations, "there should be no key for this geoid")

    def test_pop_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle()
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh)
        sim_after_pop, veh_after_pop = sim.pop_vehicle(veh.id)

        self.assertEqual(len(sim.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_pop.vehicles), 0, "the vehicle should have been removed")
        self.assertEqual(veh, veh_after_pop, "should be the same vehicle that gets popped")

    def test_add_station(self):
        station = SimulationStateTestAssets.mock_station()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_station = sim.add_station(station)

        self.assertEqual(len(sim_after_station.stations), 1, "the sim should have one station added")
        self.assertEqual(sim_after_station.stations[station.id], station, "the station should not have been mutated")

        at_loc = sim_after_station.s_locations[station.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 station at this location")
        self.assertEqual(at_loc[0], station.id, "the station's id should be found at it's geoid")

    def test_remove_station(self):
        station = SimulationStateTestAssets.mock_station()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_remove = sim.add_station(station).remove_station(station.id)

        self.assertNotIn(station.id, sim_after_remove.stations, "station should be removed")
        self.assertNotIn(station.geoid, sim_after_remove.s_locations, "nothing should be left at geoid")

    def test_add_base(self):
        base = SimulationStateTestAssets.mock_base()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_base = sim.add_base(base)

        self.assertEqual(len(sim_after_base.bases), 1, "the sim should have one base added")
        self.assertEqual(sim_after_base.bases[base.id], base, "the base should not have been mutated")

        at_loc = sim_after_base.b_locations[base.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 base at this location")
        self.assertEqual(at_loc[0], base.id, "the base's id should be found at it's geoid")

    def test_remove_base(self):
        base = SimulationStateTestAssets.mock_base()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_after_remove = sim.add_base(base).remove_base(base.id)

        self.assertNotIn(base.id, sim_after_remove.bases, "base should be removed")
        self.assertNotIn(base.geoid, sim_after_remove.b_locations, "nothing should be left at geoid")

    def test_update_road_network(self):
        sim = SimulationStateTestAssets.mock_empty_sim()
        update_time_argument = 1999
        updated_sim = sim.update_road_network(update_time_argument)
        updated_road_network = cast(SimulationStateTestAssets.MockRoadNetwork, updated_sim.road_network)
        self.assertEqual(updated_road_network.updated_to_time_step, update_time_argument)

    def test_at_vehicle_geoid(self):
        somewhere = Coordinate(90, 90)
        somewhere_else = Coordinate(0, 0)
        veh = SimulationStateTestAssets.mock_vehicle(position=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere)
        sta = SimulationStateTestAssets.mock_station(coordinate=somewhere)
        b = SimulationStateTestAssets.mock_base(coordinate=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req).add_station(sta).add_base(b)

        result = sim.at_geoid(veh.geoid)
        self.assertIn(veh.id, result['vehicles'], "should have found this vehicle")
        self.assertIn(req.id, result['requests'], "should have found this request")
        self.assertIn(sta.id, result['stations'], "should have found this station")
        self.assertNotIn(b.id, result['bases'], "should not have found this base")

    def test_vehicle_at_request(self):
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

    def test_board_vehicle(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(51, 50))
        req = SimulationStateTestAssets.mock_request(origin=Coordinate(51, 50), passengers=2)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)

        sim_boarded = sim.board_vehicle(req.id, veh.id)

        # check that both passengers boarded correctly
        for passenger in req.passengers:
            self.assertTrue(passenger.id in sim_boarded.vehicles[veh.id].passengers)
            self.assertEqual(sim_boarded.vehicles[veh.id].passengers[passenger.id].vehicle_id,
                             veh.id,
                             f"the passenger should now reference it's vehicle id")

        # request should have been removed
        self.assertNotIn(req.id, sim_boarded.requests, "request should be removed from sim")

    @skip("step expects engines, EngineIds, Chargers and assoc. logic to exist; sadly, they do not")
    def test_step(self):
        veh = SimulationStateTestAssets.mock_vehicle(position=Coordinate(0, 0))
        veh_route_step = Link(Coordinate(1, 0), 1)
        veh_repositioning = veh.transition(VehicleState.REPOSITIONING)._replace(route=Route((veh_route_step,), 1, 1))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh_repositioning)

        updated_sim = sim.step()
        expected_veh_geoid = h3.geo_to_h3(veh_route_step.position.lat,
                                          veh_route_step.position.lon,
                                          sim.sim_h3_resolution)

        self.assertIn(expected_veh_geoid, updated_sim.v_locations, "vehicle should have moved locations")


class SimulationStateTestAssets:
    h3_resolution = 11

    class MockRoadNetwork(RoadNetwork):
        updated_to_time_step: int = 0

        def route(self, origin: LinkId, destination: LinkId) -> Route:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            updated = copy.deepcopy(self)
            updated.updated_to_time_step = sim_time
            return updated

        def geoid_to_position(self, coordinate: Coordinate) -> LinkId:
            return coordinate

        def link_id_to_geoid(self, link_id: LinkId) -> Coordinate:
            return link_id

        def geoid_within_geofence(self, coordinate: Coordinate) -> bool:
            return True

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            return True

        def geoid_within_simulation(self, coordinate: Coordinate) -> bool:
            return True

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            return True

    class MockPowertrain(Powertrain):
        """
        i haven't made instances of Engine yet. 20191106-rjf
        """

        def route_energy_cost(self, route: Route) -> KwH:
            return len(route.route)

        def segment_energy_cost(self, segment: Link) -> KwH:
            return 1.0

    @classmethod
    def mock_request(cls,
                     request_id="r1",
                     origin: Coordinate = Coordinate(lat=0.0, lon=0.0),
                     destination: Coordinate = Coordinate(lat=3.0, lon=4.0),
                     passengers: int = 2) -> Request:
        o_geoid = h3.geo_to_h3(origin.lat, origin.lon, cls.h3_resolution)
        d_geoid = h3.geo_to_h3(destination.lat, destination.lon, cls.h3_resolution)

        return Request.build(
            request_id=request_id,
            origin=origin,
            destination=destination,
            origin_geoid=o_geoid,
            destination_geoid=d_geoid,
            departure_time=28800,
            cancel_time=29400,
            passengers=passengers
        )

    @classmethod
    def mock_vehicle(cls,
                     vehicle_id="m1",
                     position: LinkId = Coordinate(0, 0)) -> Vehicle:
        geoid = h3.geo_to_h3(position.lat, position.lon, cls.h3_resolution)
        return Vehicle(
            vehicle_id,
            cls.MockPowertrain(),
            EnergySource.build("battery", 100),
            position,
            geoid
        )

    @classmethod
    def mock_station(cls,
                     station_id="s1",
                     coordinate: Coordinate = Coordinate(10, 0)) -> Station:
        geoid = h3.geo_to_h3(coordinate.lat, coordinate.lon, cls.h3_resolution)
        return Station(station_id, coordinate, geoid)

    @classmethod
    def mock_base(cls, base_id="b1", coordinate: Coordinate = Coordinate(3, 3)) -> Base:
        geoid = h3.geo_to_h3(coordinate.lat, coordinate.lon, cls.h3_resolution)
        return Base(base_id, coordinate, geoid)

    @classmethod
    def mock_empty_sim(cls) -> SimulationState:
        sim, failures = initial_simulation_state(cls.MockRoadNetwork())
        assert len(failures) == 0, f"default sim used for tests had failures:\n {failures}"
        return sim
