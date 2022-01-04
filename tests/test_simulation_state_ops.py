from unittest import TestCase

from hive.resources.mock_lobster import *


class TestSimulationStateOps(TestCase):
    def test_add_request(self):
        req = mock_request()
        sim = mock_sim()
        error, sim_with_req = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(error, "should be no error")
        self.assertEqual(len(sim.requests), 0,
                         "the original sim object should not have been mutated")
        self.assertEqual(sim_with_req.requests[req.id], req,
                         "request contents should be idempotent")

        at_loc = sim_with_req.r_locations[req.origin]

        self.assertEqual(len(at_loc), 1, "should only have 1 request at this location")
        self.assertIn(req.id, at_loc, "the request's id should be found at it's geoid")

    def test_remove_request(self):
        req = mock_request()
        sim = mock_sim()
        e1, sim_with_req = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(e1, "test invariant did not hold")

        e2, sim_after_remove = simulation_state_ops.remove_request(sim_with_req, req.id)

        self.assertIsNone(e2, "should be no error")
        self.assertEqual(len(sim_with_req.requests), 1,
                         "the sim with req added should not have been mutated")
        self.assertEqual(len(sim_after_remove.requests), 0, "the request should have been removed")

        self.assertNotIn(req.origin, sim_after_remove.r_locations,
                         "there should be no key for this geoid")

    def test_modify_request(self):
        req = mock_request()
        veh = mock_vehicle()
        sim = mock_sim(vehicles=(veh, ))
        e1, sim_with_req = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(e1, "test invariant did not hold")
        current_time = sim.sim_time

        updated_req_to_set = req.assign_dispatched_vehicle(veh.id, current_time)
        e2, sim_after_modify = simulation_state_ops.modify_request(sim_with_req, updated_req_to_set)

        updated_req = sim_after_modify.requests.get(req.id)
        self.assertIsNone(e2, "should be no error")
        self.assertEqual(updated_req.dispatched_vehicle, veh.id,
                         "the request in the sim should have been modified")

    def test_modify_request_no_previous_request(self):
        req = mock_request()
        veh = mock_vehicle()
        sim = mock_sim(vehicles=(veh, ))
        current_time = sim.sim_time

        updated_req_to_set = req.assign_dispatched_vehicle(veh.id, current_time)
        e2, sim_after_modify = simulation_state_ops.modify_request(sim, updated_req_to_set)

        self.assertIsNotNone(e2, "should be an error")
        self.assertIsNone(sim_after_modify)

    def test_remove_request_multiple_at_loc(self):
        """
        confirms that we didn't remove other requests at the same location
        """
        req1 = mock_request(request_id="1")
        req2 = mock_request(request_id="2")
        sim = mock_sim()
        _, sim_with_req1 = simulation_state_ops.add_request(sim, req1)
        _, sim_with_reqs = simulation_state_ops.add_request(sim_with_req1, req2)
        error, sim_remove_req1 = simulation_state_ops.remove_request(sim_with_reqs, req1.id)

        self.assertIsNone(error, "should be no error")
        self.assertIn(req2.origin, sim_remove_req1.r_locations,
                      "geoid related to both reqs should still exist")
        self.assertIn(req2.id, sim_remove_req1.r_locations[req2.origin],
                      "req2.id should still be found in r_locations")

    def test_add_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        error, sim_with_veh = simulation_state_ops.add_vehicle(sim, veh)

        self.assertIsNone(error, "should be no error")
        self.assertEqual(len(sim.vehicles), 0,
                         "the original sim object should not have been mutated")
        self.assertEqual(sim_with_veh.vehicles[veh.id], veh,
                         "the vehicle should not have been mutated")

        at_loc = sim_with_veh.v_locations[veh.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 vehicle at this location")
        self.assertIn(veh.id, at_loc, "the vehicle's id should be found at it's geoid")

    def test_update_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        e1, sim_with_veh = simulation_state_ops.add_vehicle(sim, veh)
        self.assertIsNone(e1, "test invariant failed")

        # modify some value on the vehicle
        updated_vehicle = veh._replace(mechatronics_id="test_update")

        e2, sim_after_update = simulation_state_ops.modify_vehicle(sim_with_veh, updated_vehicle)

        self.assertIsNone(e2, "should not have an error")
        # confirm sim reflects changes to vehicle
        self.assertEqual(sim_after_update.vehicles[veh.id].mechatronics_id, "test_update",
                         "new vehicle was not updated correctly")

    def test_remove_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        e1, sim_with_veh = simulation_state_ops.add_vehicle(sim, veh)
        self.assertIsNone(e1, "test invariant failed")

        error, sim_after_remove = simulation_state_ops.remove_vehicle(sim_with_veh, veh.id)

        self.assertIsNone(error, "should have no error")
        self.assertEqual(len(sim_with_veh.vehicles), 1,
                         "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_remove.vehicles), 0, "the vehicle should have been removed")

        self.assertNotIn(veh.geoid, sim_after_remove.v_locations,
                         "there should be no key for this geoid")

    def test_pop_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        e1, sim_with_veh = simulation_state_ops.add_vehicle(sim, veh)
        self.assertIsNone(e1, "test invariant failed")
        e2, (sim_after_pop, veh_after_pop) = simulation_state_ops.pop_vehicle(sim_with_veh, veh.id)

        self.assertIsNone(e2, "should have no error")
        self.assertEqual(len(sim_with_veh.vehicles), 1,
                         "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_pop.vehicles), 0, "the vehicle should have been removed")
        self.assertEqual(veh, veh_after_pop, "should be the same vehicle that gets popped")

    def test_add_station(self):
        station = mock_station()
        sim = mock_sim()
        error, sim_after_station = simulation_state_ops.add_station(sim, station)

        self.assertIsNone(error, "should have no error")
        self.assertEqual(len(sim_after_station.stations), 1,
                         "the sim should have one station added")
        self.assertEqual(sim_after_station.stations[station.id], station,
                         "the station should not have been mutated")

        at_loc = sim_after_station.s_locations[station.geoid]

        self.assertIn(station.id, at_loc, "the station's id should be found at it's geoid")

    def test_remove_station(self):
        station = mock_station()
        sim = mock_sim(stations=(station, ))
        error, sim_after_remove = simulation_state_ops.remove_station(sim, station.id)

        self.assertIsNone(error, "should have no error")
        self.assertNotIn(station.id, sim_after_remove.stations, "station should be removed")
        self.assertNotIn(station.geoid, sim_after_remove.s_locations,
                         "nothing should be left at geoid")

    def test_update_station(self):
        station = mock_station()
        sim = mock_sim(stations=(station, ))
        new_position = EntityPosition("test", station.geoid)
        updated_station = station._replace(position=new_position)
        error, sim_after_station = simulation_state_ops.modify_station(sim, updated_station)
        self.assertIsNone(error, "should have no error")

        updated_station_in_sim = sim_after_station.stations[station.id]
        self.assertEqual(updated_station_in_sim.position, updated_station.position,
                         "station should have been updated")

        at_loc = sim_after_station.s_locations[station.geoid]
        self.assertIn(station.id, at_loc, "the station's id should be found at it's geoid")

    def test_add_base(self):
        base = mock_base()
        sim = mock_sim()
        error, sim_after_base = simulation_state_ops.add_base(sim, base)

        self.assertIsNone(error, "should have no error")
        self.assertEqual(len(sim_after_base.bases), 1, "the sim should have one base added")
        self.assertEqual(sim_after_base.bases[base.id], base,
                         "the base should not have been mutated")

        at_loc = sim_after_base.b_locations[base.geoid]

        self.assertIn(base.id, at_loc, "the base's id should be found at it's geoid")

    def test_remove_base(self):
        base = mock_base()
        sim = mock_sim(bases=(base, ))
        error, sim_after_remove = simulation_state_ops.remove_base(sim, base.id)

        self.assertIsNone(error, "should have no error")
        self.assertNotIn(base.id, sim_after_remove.bases, "base should be removed")
        self.assertNotIn(base.geoid, sim_after_remove.b_locations,
                         "nothing should be left at geoid")
