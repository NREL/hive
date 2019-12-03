import copy
from typing import cast, Optional
from unittest import TestCase, skip

from h3 import h3

from hive.model.base import Base
from hive.model.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.coordinate import Coordinate
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain import Powertrain
from hive.model.request import Request
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.station import Station
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle

from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import Route
from hive.model.roadnetwork.link import Link
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

        at_loc = sim_with_req.r_locations[req.origin]

        self.assertEqual(len(at_loc), 1, "should only have 1 request at this location")
        self.assertEqual(at_loc[0], req.id, "the request's id should be found at it's geoid")

    def test_remove_request(self):
        req = SimulationStateTestAssets.mock_request()
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_req = sim.add_request(req)
        sim_after_remove = sim_with_req.remove_request(req.id)

        self.assertEqual(len(sim_with_req.requests), 1, "the sim with req added should not have been mutated")
        self.assertEqual(len(sim_after_remove.requests), 0, "the request should have been removed")

        self.assertNotIn(req.origin, sim_after_remove.r_locations, "there should be no key for this geoid")

    def test_remove_request_multiple_at_loc(self):
        """
        confirms that we didn't remove other requests at the same location
        """
        req1 = SimulationStateTestAssets.mock_request(request_id="1")
        req2 = SimulationStateTestAssets.mock_request(request_id="2")
        sim = SimulationStateTestAssets.mock_empty_sim()
        sim_with_reqs = sim.add_request(req1).add_request(req2)
        sim_remove_req1 = sim_with_reqs.remove_request(req1.id)

        self.assertIn(req2.origin,
                      sim_remove_req1.r_locations,
                      "geoid related to both reqs should still exist")
        self.assertIn(req2.id,
                      sim_remove_req1.r_locations[req2.origin],
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
        sim_before_update = sim.add_vehicle(veh)

        # modify some values on the vehicle
        new_soc_lower_limit = 0.5
        new_geoid = h3.geo_to_h3(39.77, -105, sim_before_update.sim_h3_resolution)
        updated_vehicle = veh._replace(geoid=new_geoid,
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
        self.assertIsInstance(updated_road_network, SimulationStateTestAssets.MockRoadNetwork)

    def test_at_vehicle_geoid(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere)
        sta = SimulationStateTestAssets.mock_station(geoid=somewhere)
        b = SimulationStateTestAssets.mock_base(geoid=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req).add_station(sta).add_base(b)

        result = sim.at_geoid(veh.geoid)
        self.assertIn(veh.id, result['vehicles'], "should have found this vehicle")
        self.assertIn(req.id, result['requests'], "should have found this request")
        self.assertIn(sta.id, result['stations'], "should have found this station")
        self.assertNotIn(b.id, result['bases'], "should not have found this base")

    def test_vehicle_at_request(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertTrue(result, "the vehicle should be at the request")

    def test_vehicle_not_at_request(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertFalse(result, "the vehicle should not be at the request")

    def test_vehicle_at_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        sta = SimulationStateTestAssets.mock_station(geoid=somewhere)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertTrue(result, "the vehicle should be at the station")

    def test_vehicle_not_at_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        sta = SimulationStateTestAssets.mock_station(geoid=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertFalse(result, "the vehicle should not be at the station")

    def test_vehicle_at_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        base = SimulationStateTestAssets.mock_base(geoid=somewhere)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertTrue(result, "the vehicle should be at the base")

    def test_vehicle_not_at_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        base = SimulationStateTestAssets.mock_base(geoid=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertFalse(result, "the vehicle should not be at the base")

    def test_board_vehicle(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere, passengers=2)
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

    def test_perform_vehicle_state_transformation_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        bas = SimulationStateTestAssets.mock_base(geoid=somewhere)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(bas)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.RESERVE_BASE)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.RESERVE_BASE)

    def test_perform_vehicle_state_transformation_base_no_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        bas = SimulationStateTestAssets.mock_base(geoid=somewhere)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_base(bas)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.RESERVE_BASE)

        self.assertIsNone(sim_updated)

    def test_perform_vehicle_state_transformation_charge(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        sta = SimulationStateTestAssets.mock_station(geoid=somewhere)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.CHARGING_STATION)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.CHARGING_STATION)

    def test_perform_vehicle_state_transformation_charge_no_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        sta = SimulationStateTestAssets.mock_station(geoid=somewhere)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere_else)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_station(sta)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.CHARGING_STATION)

        self.assertIsNone(sim_updated)

    def test_perform_vehicle_state_transformation_serve_trip(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere, passengers=2)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.SERVICING_TRIP, req.destination)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.SERVICING_TRIP)

        self.assertTrue(updated_veh.has_route())

    def test_perform_vehicle_state_transformation_serve_trip_no_reqs(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        req = SimulationStateTestAssets.mock_request(origin=somewhere_else, passengers=2)
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh).add_request(req)

        sim_updated = sim.perform_vehicle_state_transformation(veh.id, VehicleState.SERVICING_TRIP, req.destination)

        self.assertIsNone(sim_updated)

    @skip("step expects engines, EngineIds, Chargers and assoc. logic to exist; sadly, they do not")
    def test_step(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = SimulationStateTestAssets.mock_vehicle(geoid=somewhere)
        veh_route_step = Link(Coordinate(1, 0), 1)
        veh_repositioning = veh.transition(VehicleState.REPOSITIONING)._replace(route=Route((veh_route_step,), 1, 1))
        sim = SimulationStateTestAssets.mock_empty_sim().add_vehicle(veh_repositioning)

        updated_sim = sim.step()
        expected_veh_geoid = h3.geo_to_h3(veh_route_step.position.lat,
                                          veh_route_step.position.lon,
                                          sim.sim_h3_resolution)

        self.assertIn(expected_veh_geoid, updated_sim.v_locations, "vehicle should have moved locations")


class SimulationStateTestAssets:
    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: PropertyLink, destination: PropertyLink) -> Route:
            start = origin.link.start
            end = destination.link.end
            return (PropertyLink("mpl", Link("ml", start, end), 1, 1, 1), )

        def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
            return PropertyLink("mpl", Link("ml", geoid, geoid), 1, 1, 1)

        def update(self, sim_time: Time) -> RoadNetwork:
            return self

        def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
            pass

        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            return True

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            return True

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            return True

        def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
            raise NotImplementedError("implement if needed for testing")

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            return True


    class MockPowertrain(Powertrain):
        def get_id(self) -> PowertrainId:
            return "mock_powertrain"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def energy_cost(self, route: Route) -> Kw:
            return len(route)

    @classmethod
    def mock_request(cls,
                     request_id="r1",
                     origin: GeoId = h3.geo_to_h3(39.74, -105, 15),
                     destination: GeoId = h3.geo_to_h3(39.76, -105, 15),
                     passengers: int = 2) -> Request:
        return Request.build(
            request_id=request_id,
            origin=origin,
            destination=destination,
            departure_time=28800,
            cancel_time=29400,
            passengers=passengers
        )

    @classmethod
    def mock_vehicle(cls,
                     vehicle_id="m1",
                     geoid: GeoId = h3.geo_to_h3(39.75, -105, 15)) -> Vehicle:
        mock_powertrain = cls.MockPowertrain()
        mock_property_link = cls.MockRoadNetwork().property_link_from_geoid(geoid)
        mock_veh = Vehicle(vehicle_id,
                           mock_powertrain.get_id(),
                           EnergySource.build(EnergyType.ELECTRIC, 40, 1),
                           geoid,
                           mock_property_link,
                           )
        return mock_veh

    @classmethod
    def mock_station(cls,
                     station_id="s1",
                     geoid: GeoId = h3.geo_to_h3(39.75, -105.01, 15)) -> Station:
        return Station.build(station_id, geoid, {Charger.LEVEL_2: 5})

    @classmethod
    def mock_base(cls, base_id="b1", geoid: GeoId = h3.geo_to_h3(39.73, -105, 15)) -> Base:
        return Base.build(base_id, geoid, None, 5)

    @classmethod
    def mock_empty_sim(cls) -> SimulationState:
        sim, failures = initial_simulation_state(cls.MockRoadNetwork())
        assert len(failures) == 0, f"default sim used for tests had failures:\n {failures}"
        return sim
