from unittest import TestCase

from tests.mock_lobster import *


class TestSimulationState(TestCase):

    def test_add_request(self):
        req = mock_request()
        sim = mock_sim()
        sim_with_req = sim.add_request(req)
        self.assertEqual(len(sim.requests), 0, "the original sim object should not have been mutated")
        self.assertEqual(sim_with_req.requests[req.id], req, "request contents should be idempotent")

        at_loc = sim_with_req.r_locations[req.origin]

        self.assertEqual(len(at_loc), 1, "should only have 1 request at this location")
        self.assertEqual(at_loc[0], req.id, "the request's id should be found at it's geoid")

    def test_remove_request(self):
        req = mock_request()
        sim = mock_sim()
        sim_with_req = sim.add_request(req)
        sim_after_remove = sim_with_req.remove_request(req.id)

        self.assertEqual(len(sim_with_req.requests), 1, "the sim with req added should not have been mutated")
        self.assertEqual(len(sim_after_remove.requests), 0, "the request should have been removed")

        self.assertNotIn(req.origin, sim_after_remove.r_locations, "there should be no key for this geoid")

    def test_remove_request_multiple_at_loc(self):
        """
        confirms that we didn't remove other requests at the same location
        """
        req1 = mock_request(request_id="1")
        req2 = mock_request(request_id="2")
        sim = mock_sim()
        sim_with_reqs = sim.add_request(req1).add_request(req2)
        sim_remove_req1 = sim_with_reqs.remove_request(req1.id)

        self.assertIn(req2.origin,
                      sim_remove_req1.r_locations,
                      "geoid related to both reqs should still exist")
        self.assertIn(req2.id,
                      sim_remove_req1.r_locations[req2.origin],
                      "req2.id should still be found in r_locations")

    def test_add_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        sim_with_veh = sim.add_vehicle(veh)

        self.assertEqual(len(sim.vehicles), 0, "the original sim object should not have been mutated")
        self.assertEqual(sim_with_veh.vehicles[veh.id], veh, "the vehicle should not have been mutated")

        at_loc = sim_with_veh.v_locations[veh.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 vehicle at this location")
        self.assertEqual(at_loc[0], veh.id, "the vehicle's id should be found at it's geoid")

    def test_update_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        sim_before_update = sim.add_vehicle(veh)

        # modify some value on the vehicle
        updated_powertrain_id = "testing an update"
        updated_vehicle = veh._replace(powertrain_id=updated_powertrain_id)

        sim_after_update = sim_before_update.modify_vehicle(updated_vehicle)

        # confirm sim reflects changes to vehicle
        self.assertEqual(sim_after_update.vehicles[veh.id].powertrain_id,
                         updated_powertrain_id,
                         "new vehicle powertrain_id was not updated correctly")

    def test_remove_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim()
        sim_with_veh = sim.add_vehicle(veh)
        sim_after_remove = sim_with_veh.remove_vehicle(veh.id)

        self.assertEqual(len(sim_with_veh.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_remove.vehicles), 0, "the vehicle should have been removed")

        self.assertNotIn(veh.geoid, sim_after_remove.v_locations, "there should be no key for this geoid")

    def test_pop_vehicle(self):
        veh = mock_vehicle()
        sim = mock_sim().add_vehicle(veh)
        sim_after_pop, veh_after_pop = sim.pop_vehicle(veh.id)

        self.assertEqual(len(sim.vehicles), 1, "the sim with vehicle added should not have been mutated")
        self.assertEqual(len(sim_after_pop.vehicles), 0, "the vehicle should have been removed")
        self.assertEqual(veh, veh_after_pop, "should be the same vehicle that gets popped")

    def test_add_station(self):
        station = mock_station()
        sim = mock_sim()
        sim_after_station = sim.add_station(station)

        self.assertEqual(len(sim_after_station.stations), 1, "the sim should have one station added")
        self.assertEqual(sim_after_station.stations[station.id], station, "the station should not have been mutated")

        at_loc = sim_after_station.s_locations[station.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 station at this location")
        self.assertEqual(at_loc[0], station.id, "the station's id should be found at it's geoid")

    def test_remove_station(self):
        station = mock_station()
        sim = mock_sim()
        sim_after_remove = sim.add_station(station).remove_station(station.id)

        self.assertNotIn(station.id, sim_after_remove.stations, "station should be removed")
        self.assertNotIn(station.geoid, sim_after_remove.s_locations, "nothing should be left at geoid")

    def test_add_base(self):
        base = mock_base()
        sim = mock_sim()
        sim_after_base = sim.add_base(base)

        self.assertEqual(len(sim_after_base.bases), 1, "the sim should have one base added")
        self.assertEqual(sim_after_base.bases[base.id], base, "the base should not have been mutated")

        at_loc = sim_after_base.b_locations[base.geoid]

        self.assertEqual(len(at_loc), 1, "should only have 1 base at this location")
        self.assertEqual(at_loc[0], base.id, "the base's id should be found at it's geoid")

    def test_remove_base(self):
        base = mock_base()
        sim = mock_sim()
        sim_after_remove = sim.add_base(base).remove_base(base.id)

        self.assertNotIn(base.id, sim_after_remove.bases, "base should be removed")
        self.assertNotIn(base.geoid, sim_after_remove.b_locations, "nothing should be left at geoid")

    def test_update_road_network(self):
        sim = mock_sim()
        update_time_argument = 1999
        updated_sim = sim.update_road_network(update_time_argument)
        updated_road_network = updated_sim.road_network
        self.assertIsInstance(updated_road_network, HaversineRoadNetwork)

    def test_at_vehicle_geoid(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere)
        b = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_request(req).add_station(sta).add_base(b)

        result = sim.at_geoid(veh.geoid)
        self.assertIn(veh.id, result['vehicles'], "should have found this vehicle")
        self.assertIn(req.id, result['requests'], "should have found this request")
        self.assertIn(sta.id, result['stations'], "should have found this station")
        self.assertNotIn(b.id, result['bases'], "should not have found this base")

    def test_vehicle_at_request(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertTrue(result, "the vehicle should be at the request")

    def test_vehicle_not_at_request(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_request(req)
        result = sim.vehicle_at_request(veh.id, req.id)
        self.assertFalse(result, "the vehicle should not be at the request")

    def test_vehicle_at_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertTrue(result, "the vehicle should be at the station")

    def test_vehicle_not_at_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_station(sta)
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertFalse(result, "the vehicle should not be at the station")

    def test_vehicle_at_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertTrue(result, "the vehicle should be at the base")

    def test_vehicle_not_at_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_base(base)
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertFalse(result, "the vehicle should not be at the base")

    def test_board_vehicle(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere, passengers=2)
        sim = mock_sim().add_vehicle(veh).add_request(req)

        sim_boarded = sim.board_vehicle(req.id, veh.id)

        # check that both passengers boarded correctly
        for passenger in req.passengers:
            self.assertTrue(passenger.id in sim_boarded.vehicles[veh.id].passengers)
            self.assertEqual(sim_boarded.vehicles[veh.id].passengers[passenger.id].vehicle_id,
                             veh.id,
                             f"the passenger should now reference it's vehicle id")

        # request should have been removed
        self.assertNotIn(req.id, sim_boarded.requests, "request should be removed from sim")

    def test_set_vehicle_intention_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        bas = mock_base_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh).add_base(bas)

        instruction = Instruction(veh.id, VehicleState.RESERVE_BASE)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.RESERVE_BASE)

    def test_set_vehicle_intention_base_no_base(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        bas = mock_base_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_base(bas)

        instruction = Instruction(veh.id, VehicleState.RESERVE_BASE)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNone(sim_updated)

    def test_set_vehicle_intention_charge(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh).add_station(sta)

        instruction = Instruction(veh.id,
                                  VehicleState.CHARGING_STATION,
                                  station_id=sta.id,
                                  charger=Charger.DCFC)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.CHARGING_STATION)

    def test_set_vehicle_intention_charge_no_station(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_station(sta)

        instruction = Instruction(veh.id,
                                  VehicleState.CHARGING_STATION,
                                  station_id=sta.id,
                                  charger=Charger.DCFC)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNone(sim_updated)

    def test_set_vehicle_intention_serve_trip(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere, passengers=2)
        sim = mock_sim().add_vehicle(veh).add_request(req)

        instruction = Instruction(veh.id,
                                  VehicleState.SERVICING_TRIP,
                                  request_id=req.id)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertEqual(updated_veh.vehicle_state, VehicleState.SERVICING_TRIP)

        self.assertTrue(updated_veh.has_route())

    def test_set_vehicle_intention_serve_trip_no_reqs(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else, passengers=2)
        sim = mock_sim().add_vehicle(veh).add_request(req)

        instruction = Instruction(veh.id,
                                  VehicleState.SERVICING_TRIP,
                                  request_id=req.id)
        sim_updated = sim.apply_instruction(instruction)

        self.assertIsNone(sim_updated)

    def test_step_moving_vehicle(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere,
                                       destination=somewhere_else,
                                       passengers=2)
        sim = mock_sim().add_vehicle(veh).add_request(req)

        instruction = Instruction(veh.id,
                                  VehicleState.SERVICING_TRIP,
                                  request_id=req.id)
        sim_moving_veh = sim.apply_instruction(instruction).step_simulation()

        moved_veh = sim_moving_veh.vehicles[veh.id]

        self.assertNotEqual(veh.geoid, moved_veh.geoid, 'Vehicle should have moved')
        self.assertGreater(veh.energy_source.soc,
                           moved_veh.energy_source.soc,
                           'Vehicle should consume energy while moving.')

    def test_step_charging_vehicle(self):
        somewhere = h3.geo_to_h3(39.75, -105.01, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh).add_station(sta)

        instruction = Instruction(veh.id,
                                  VehicleState.CHARGING_STATION,
                                  station_id=sta.id,
                                  charger=Charger.DCFC)
        sim_charging_veh = sim.apply_instruction(instruction).step_simulation()

        charged_veh = sim_charging_veh.vehicles[veh.id]

        self.assertGreater(charged_veh.energy_source.soc,
                           veh.energy_source.soc,
                           "Vehicle should have gained energy")

    def test_step_idle_vehicle(self):
        veh = mock_vehicle_from_geoid()
        sim = mock_sim().add_vehicle(veh)

        sim_idle_veh = sim.step_simulation()

        idle_veh = sim_idle_veh.vehicles[veh.id]

        self.assertLess(idle_veh.energy_source.soc,
                        veh.energy_source.soc,
                        "Idle vehicle should have consumed energy")

    def test_terminal_state_ending_trip(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.5)
        req = mock_request_from_geoids(origin=somewhere,
                                       destination=somewhere_else,
                                       passengers=2)
        sim = mock_sim(sim_timestep_duration_seconds=1000).add_vehicle(veh).add_request(req)
        instruction = Instruction(veh.id,
                                  VehicleState.SERVICING_TRIP,
                                  request_id=req.id)
        sim_with_instruction = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim_with_instruction, "Vehicle should have transitioned to servicing trip")

        sim_veh_at_dest_servicing = sim_with_instruction.step_simulation()  # gets to end of trip
        sim_idle = sim_veh_at_dest_servicing.step_simulation()  # actually transitions to IDLE

        idle_veh = sim_idle.vehicles[veh.id]

        self.assertEqual(idle_veh.vehicle_state, VehicleState.IDLE, "Vehicle should have transitioned to idle.")
        self.assertEqual(idle_veh.geoid, req.destination, "Vehicle should be at request destination.")
        self.assertEqual(idle_veh.has_passengers(), False, "Vehicle should not have any passengers.")
        self.assertEqual(req.id not in sim_idle.requests, True, "Request should have been removed from simulation.")

    def test_terminal_state_starting_trip(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else,
                                       destination=somewhere,
                                       passengers=2)
        sim = mock_sim().add_vehicle(veh).add_request(req)
        instruction = Instruction(veh.id,
                                  VehicleState.DISPATCH_TRIP,
                                  request_id=req.id)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        # should take about 800 seconds to arrive at trip origin, and
        # 1 more state step of any size to transition state

        sim_at_req = sim._replace(sim_timestep_duration_seconds=800).step_simulation()
        sim_with_req = sim_at_req._replace(sim_timestep_duration_seconds=1).step_simulation()

        tripping_veh = sim_with_req.vehicles[veh.id]

        self.assertEqual(tripping_veh.vehicle_state, VehicleState.SERVICING_TRIP)

        # should take about 800 seconds to arrive at trip destination, and
        # 1 more state step of any size to transition state
        sim_at_dest = sim_with_req._replace(sim_timestep_duration_seconds=800).step_simulation()
        sim_idle = sim_at_dest._replace(sim_timestep_duration_seconds=1).step_simulation()

        idle_veh = sim_idle.vehicles[veh.id]

        self.assertEqual(idle_veh.vehicle_state, VehicleState.IDLE, "Vehicle should have transitioned to idle.")
        self.assertEqual(idle_veh.geoid, req.destination, "Vehicle should be at request destination.")
        self.assertEqual(idle_veh.has_passengers(), False, "Vehicle should not have any passengers.")
        self.assertEqual(req.id not in sim_idle.requests, True, "Request should have been removed from simulation.")

    def test_terminal_state_dispatch_station(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(station_id='s1', geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_station(sta)

        instruction = Instruction(veh.id,
                                  VehicleState.DISPATCH_STATION,
                                  station_id=sta.id,
                                  charger=Charger.DCFC)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        sim_at_sta = sim._replace(sim_timestep_duration_seconds=1000).step_simulation()
        sim_in_sta = sim_at_sta._replace(sim_timestep_duration_seconds=1).step_simulation()

        charging_veh = sim_in_sta.vehicles[veh.id]
        station_w_veh = sim_in_sta.stations[sta.id]

        self.assertEqual(charging_veh.vehicle_state,
                         VehicleState.CHARGING_STATION,
                         "Vehicle should have transitioned to charging.")
        self.assertEqual(charging_veh.geoid, sta.geoid, "Vehicle should be at station.")
        self.assertLess(station_w_veh.available_chargers[Charger.DCFC],
                        station_w_veh.total_chargers[Charger.DCFC],
                        "Station should have charger in use.")

    def test_terminal_state_dispatch_base(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(base_id='b1', geoid=somewhere_else)
        sim = mock_sim().add_vehicle(veh).add_base(base)

        instruction = Instruction(veh.id,
                                  VehicleState.DISPATCH_BASE,
                                  location=base.geoid)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_base = sim._replace(sim_timestep_duration_seconds=1000).step_simulation()
        sim_in_base = sim_at_base._replace(sim_timestep_duration_seconds=1).step_simulation()

        veh_at_base = sim_in_base.vehicles[veh.id]

        self.assertEqual(veh_at_base.vehicle_state,
                         VehicleState.RESERVE_BASE,
                         "Vehicle should have transitioned to RESERVE_BASE")
        self.assertEqual(veh_at_base.geoid,
                         base.geoid,
                         "Vehicle should be located at base")

    def test_terminal_state_repositioning(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim().add_vehicle(veh)

        instruction = Instruction(veh.id,
                                  VehicleState.REPOSITIONING,
                                  location=somewhere_else)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_new_pos = sim._replace(sim_timestep_duration_seconds=1000).step_simulation()
        sim_in_new_state = sim_at_new_pos._replace(sim_timestep_duration_seconds=1).step_simulation()

        veh_at_new_loc = sim_in_new_state.vehicles[veh.id]

        self.assertEqual(veh_at_new_loc.vehicle_state,
                         VehicleState.IDLE,
                         "Vehicle should have transitioned to IDLE")
        self.assertEqual(veh_at_new_loc.geoid,
                         somewhere_else,
                         "Vehicle should be located at somewhere_else")

    def test_terminal_state_charging(self):

        sta = mock_station_from_geoid()
        veh = mock_vehicle_from_geoid(
            energy_type=EnergyType.ELECTRIC,
            capacity_kwh=50,
            ideal_energy_limit_kwh=50,
            soc=0.75
        )
        sim = mock_sim().add_vehicle(veh).add_station(sta)

        instruction = Instruction(veh.id,
                                  VehicleState.CHARGING_STATION,
                                  station_id=sta.id,
                                  charger=Charger.DCFC)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        # 1000 seconds should get us charged, and 1 more sim step of any size to transition vehicle state
        sim_charged = sim._replace(sim_timestep_duration_seconds=1000).step_simulation()
        sim_in_new_state = sim_charged._replace(sim_timestep_duration_seconds=1).step_simulation()

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertEqual(fully_charged_veh.vehicle_state,
                         VehicleState.IDLE,
                         "Vehicle should have transitioned to IDLE")

    def test_terminal_state_charging_base(self):
        sta = mock_station_from_geoid()
        bas = mock_base_from_geoid(station_id=sta.id)
        veh = mock_vehicle_from_geoid(
            energy_type=EnergyType.ELECTRIC,
            capacity_kwh=50,
            ideal_energy_limit_kwh=40,
            soc=0.75
        )
        sim = mock_sim().add_vehicle(veh).add_station(sta).add_base(bas)

        instruction = Instruction(veh.id,
                                  VehicleState.CHARGING_BASE,
                                  station_id=bas.station_id,
                                  charger=Charger.DCFC)
        sim = sim.apply_instruction(instruction)

        self.assertIsNotNone(sim, "Vehicle should have set intention.")

        # 1000 seconds should get us charged, and 1 more sim step of any size to transition vehicle state
        sim_charged = sim._replace(sim_timestep_duration_seconds=1000).step_simulation()
        sim_in_new_state = sim_charged._replace(sim_timestep_duration_seconds=1).step_simulation()

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertEqual(fully_charged_veh.vehicle_state,
                         VehicleState.RESERVE_BASE,
                         "Vehicle should have transitioned to RESERVE_BASE")
