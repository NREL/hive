from unittest import TestCase

from hive.model.instruction import *
from hive.state.simulation_state.update.step_simulation import step_simulation
from tests.mock_lobster import *
from hive.state.vehicle_state import *


class TestSimulationState(TestCase):

    def test_at_vehicle_geoid(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere)
        b = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim(
            vehicles=(veh, ),
            stations=(sta, ),
            bases=(b, )
        )
        error, sim_with_request = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(error, "test invariant failed")

        result = sim_with_request.at_geoid(veh.geoid)
        self.assertIn(veh.id, result['vehicles'], "should have found this vehicle")
        self.assertIn(req.id, result['requests'], "should have found this request")
        self.assertEqual(sta.id, result['station'], "should have found this station")
        self.assertIsNone(result['base'], "should not have found this base")

    def test_vehicle_at_request(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(vehicles=(veh,))
        error, sim_with_veh = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(error, "test invariant failed")
        result = sim_with_veh.vehicle_at_request(veh.id, req.id)
        self.assertTrue(result, "the vehicle should be at the request")

    def test_vehicle_not_at_request(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else)
        sim = mock_sim(vehicles=(veh,))
        error, sim_with_veh = simulation_state_ops.add_request(sim, req)
        result = sim_with_veh.vehicle_at_request(veh.id, req.id)
        self.assertFalse(result, "the vehicle should not be at the request")

    def test_vehicle_at_station(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertTrue(result, "the vehicle should be at the station")

    def test_vehicle_not_at_station(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        result = sim.vehicle_at_station(veh.id, sta.id)
        self.assertFalse(result, "the vehicle should not be at the station")

    def test_vehicle_at_base(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,), bases=(base,))
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertTrue(result, "the vehicle should be at the base")

    def test_vehicle_not_at_base(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), bases=(base,))
        result = sim.vehicle_at_base(veh.id, base.id)
        self.assertFalse(result, "the vehicle should not be at the base")

    def test_set_vehicle_instruction_base(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        bas = mock_base_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,), bases=(bas,))
        env = mock_env()

        instruction = ReserveBaseInstruction(vehicle_id=veh.id, base_id=bas.id)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertIsInstance(updated_veh.vehicle_state, ReserveBase, "should be reserving at base")

    def test_set_vehicle_instruction_base_no_base(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        bas = mock_base_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), bases=(bas,))
        env = mock_env()

        instruction = ReserveBaseInstruction(vehicle_id=veh.id, base_id=bas.id)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNone(sim_updated)

    def test_set_vehicle_instruction_charge(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger=Charger.DCFC
        )
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim_updated)

        updated_veh = sim_updated.vehicles[veh.id]
        self.assertIsInstance(updated_veh.vehicle_state, ChargingStation)

    def test_set_vehicle_instruction_charge_no_station(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger=Charger.DCFC
        )

        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNone(sim_updated)

    def test_set_vehicle_instruction_serve_trip(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere, passengers=2)
        env = mock_env()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(veh,)), req)
        self.assertIsNone(e1, "test invariant failed")

        instruction = ServeTripInstruction(vehicle_id=veh.id, request_id=req.id)

        e2, sim_updated = instruction.apply_instruction(sim, env)
        if e2:
            self.fail(e2.args)

        self.assertIsNotNone(sim_updated)

        # should now be servicing a trip
        updated_veh = sim_updated.vehicles[veh.id]
        self.assertIsInstance(updated_veh.vehicle_state, ServicingTrip)

        veh_passengers = updated_veh.vehicle_state.passengers
        passenger_ids_in_vehicle = set(map(lambda p: p.id, veh_passengers))

        # check that both passengers boarded correctly
        for passenger in req.passengers:

            self.assertIn(passenger.id,
                          passenger_ids_in_vehicle,
                          f"passenger {passenger.id} should be in the vehicle but isn't")

        for passenger in veh_passengers:
            self.assertEqual(passenger.vehicle_id,
                             veh.id,
                             f"the passenger should now reference it's vehicle id")

        # request should have been removed
        self.assertNotIn(req.id, sim_updated.requests, "request should be removed from sim")

        self.assertTrue(len(updated_veh.vehicle_state.route) > 0, "should have a route")

    def test_set_vehicle_instruction_serve_trip_no_reqs(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else, passengers=2)
        env = mock_env()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(veh,)), req)
        self.assertIsNone(e1, "test invariant failed")

        instruction = ServeTripInstruction(vehicle_id=veh.id, request_id=req.id)
        error, sim_updated = instruction.apply_instruction(sim, env)
        self.assertIsNotNone(error, "no request at vehicle location should produce an error message")
        self.assertIsNone(sim_updated, "sim update should not have happened")

    def test_step_moving_vehicle(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere,
                                       destination=somewhere_else,
                                       passengers=2)
        env = mock_env()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(veh,)), req)
        self.assertIsNone(e1, "test invariant failed")

        instruction = ServeTripInstruction(vehicle_id=veh.id, request_id=req.id)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        sim_moving_veh = step_simulation(sim_updated, env)

        moved_veh = sim_moving_veh.vehicles[veh.id]

        self.assertNotEqual(veh.geoid, moved_veh.geoid, 'Vehicle should have moved')
        self.assertGreater(veh.energy_source.soc,
                           moved_veh.energy_source.soc,
                           'Vehicle should consume energy while moving.')

    def test_step_charging_vehicle(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger=Charger.DCFC
        )

        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        sim_charging_veh = step_simulation(sim_updated, env)

        charged_veh = sim_charging_veh.vehicles[veh.id]

        self.assertGreater(charged_veh.energy_source.soc,
                           veh.energy_source.soc,
                           "Vehicle should have gained energy")

    def test_step_idle_vehicle(self):
        veh = mock_vehicle_from_geoid()
        sim = mock_sim(vehicles=(veh,))
        env = mock_env()

        sim_idle_veh = step_simulation(sim, env)

        idle_veh = sim_idle_veh.vehicles[veh.id]

        self.assertLess(idle_veh.energy_source.soc,
                        veh.energy_source.soc,
                        "Idle vehicle should have consumed energy")

    def test_terminal_state_ending_trip(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.5)
        req = mock_request_from_geoids(origin=somewhere,
                                       destination=somewhere_else,
                                       passengers=2)
        env = mock_env()
        sim = mock_sim(sim_timestep_duration_seconds=1000, vehicles=(veh,))
        e1, sim_with_req = simulation_state_ops.add_request(sim, req)
        self.assertIsNone(e1, "test invariant failed")

        instruction = ServeTripInstruction(vehicle_id=veh.id, request_id=req.id)
        error, sim_with_instruction = instruction.apply_instruction(sim_with_req, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim_with_instruction, "Vehicle should have transitioned to servicing trip")

        sim_veh_at_dest_servicing = step_simulation(sim_with_instruction, env)  # gets to end of trip
        sim_idle = step_simulation(sim_veh_at_dest_servicing, env)  # actually transitions to IDLE

        idle_veh = sim_idle.vehicles[veh.id]

        self.assertIsInstance(idle_veh.vehicle_state, Idle, "Vehicle should have transitioned to idle.")
        self.assertEqual(idle_veh.geoid, req.destination, "Vehicle should be at request destination.")
        self.assertEqual(req.id not in sim_idle.requests, True, "Request should have been removed from simulation.")

    def test_terminal_state_starting_trip(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else,
                                       destination=somewhere,
                                       passengers=2)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(veh,)), req)
        self.assertIsNone(e1, "test invariant failed")

        instruction = DispatchTripInstruction(vehicle_id=veh.id, request_id=req.id)
        env = mock_env()
        e2, sim_updated = instruction.apply_instruction(sim, env)
        if e2:
            self.fail(e2.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # should take about 800 seconds to arrive at trip origin, and
        # 1 more state step of any size to transition state

        sim_at_req = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=800), env)
        sim_with_req = step_simulation(sim_at_req._replace(sim_timestep_duration_seconds=1), env)

        tripping_veh = sim_with_req.vehicles[veh.id]

        self.assertIsInstance(tripping_veh.vehicle_state, ServicingTrip)

        # should take about 800 seconds to arrive at trip destination, and
        # 1 more state step of any size to transition state
        sim_at_dest = step_simulation(sim_with_req._replace(sim_timestep_duration_seconds=800), env)
        sim_idle = step_simulation(sim_at_dest._replace(sim_timestep_duration_seconds=1), env)

        idle_veh = sim_idle.vehicles[veh.id]

        self.assertIsInstance(idle_veh.vehicle_state, Idle, "Vehicle should have transitioned to idle.")
        self.assertEqual(idle_veh.geoid, req.destination, "Vehicle should be at request destination.")
        self.assertEqual(req.id not in sim_idle.requests, True, "Request should have been removed from simulation.")

    def test_terminal_state_dispatch_station(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sta = mock_station_from_geoid(station_id='s1', geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = DispatchStationInstruction(vehicle_id=veh.id, station_id=sta.id, charger=Charger.DCFC)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        sim_at_sta = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_sta = step_simulation(sim_at_sta._replace(sim_timestep_duration_seconds=1), env)

        charging_veh = sim_in_sta.vehicles[veh.id]
        station_w_veh = sim_in_sta.stations[sta.id]

        self.assertIsInstance(charging_veh.vehicle_state,
                              ChargingStation,
                              "Vehicle should have transitioned to charging.")
        self.assertEqual(charging_veh.geoid, sta.geoid, "Vehicle should be at station.")
        self.assertLess(station_w_veh.available_chargers[Charger.DCFC],
                        station_w_veh.total_chargers[Charger.DCFC],
                        "Station should have charger in use.")

    def test_terminal_state_dispatch_base(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(base_id='b1', geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), bases=(base,))
        env = mock_env()

        instruction = DispatchBaseInstruction(vehicle_id=veh.id, base_id=base.id)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_base = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_base = step_simulation(sim_at_base._replace(sim_timestep_duration_seconds=1), env)

        veh_at_base = sim_in_base.vehicles[veh.id]

        self.assertIsInstance(veh_at_base.vehicle_state,
                              ReserveBase,
                              "Vehicle should have transitioned to RESERVE_BASE")
        self.assertEqual(veh_at_base.geoid,
                         base.geoid,
                         "Vehicle should be located at base")

    def test_terminal_state_repositioning(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        sim = mock_sim(vehicles=(veh,))
        env = mock_env()

        instruction = RepositionInstruction(vehicle_id=veh.id, destination=somewhere_else)
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_new_pos = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_new_state = step_simulation(sim_at_new_pos._replace(sim_timestep_duration_seconds=1), env)

        veh_at_new_loc = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(veh_at_new_loc.vehicle_state,
                              Idle,
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
        sim = mock_sim(vehicles=(veh,), stations=(sta,))

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger=Charger.DCFC
        )
        env = mock_env()
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # 1000 seconds should get us charged, and 1 more sim step of any size to transition vehicle state
        sim_charged = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_new_state = step_simulation(sim_charged._replace(sim_timestep_duration_seconds=1), env)

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(fully_charged_veh.vehicle_state,
                              Idle,
                              "Vehicle should have transitioned to IDLE")

    def test_terminal_state_charging_base(self):
        veh = mock_vehicle_from_geoid(
            energy_type=EnergyType.ELECTRIC,
            capacity_kwh=50,
            ideal_energy_limit_kwh=40,
            soc=0.75
        )
        sta = mock_station_from_geoid()
        bas = mock_base_from_geoid(station_id=sta.id)
        sim = mock_sim(vehicles=(veh,), stations=(sta,), bases=(bas,))

        instruction = ChargeBaseInstruction(
            vehicle_id=veh.id,
            base_id=bas.id,
            charger=Charger.DCFC
        )
        env = mock_env()
        error, sim_updated = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # 1000 seconds should get us charged, and 1 more sim step of any size to transition vehicle state
        sim_charged = step_simulation(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_new_state = step_simulation(sim_charged._replace(sim_timestep_duration_seconds=1), env)

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(fully_charged_veh.vehicle_state,
                              ReserveBase,
                              "Vehicle should have transitioned to RESERVE_BASE")

    def test_vehicle_runs_out_of_energy(self):

        low_energy_veh = mock_vehicle_from_geoid(soc=0.01)
        sim = mock_sim(vehicles=(low_energy_veh,))

        # costs a fixed 10 kwh to make any movement
        env = mock_env(powertrains=(mock_powertrain(energy_cost_kwh=10),))

        inbox_cafe_in_torvet_julianehab_greenland = h3.geo_to_h3(63.8002568, -53.3170783, 15)
        instruction = RepositionInstruction(DefaultIds.mock_vehicle_id(), inbox_cafe_in_torvet_julianehab_greenland)
        error, sim_instructed = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim_instructed, "test invariant failed - should be able to reposition default vehicle")

        # one movement takes more energy than this agent has
        sim_out_of_order = step_simulation(sim_instructed, env)

        veh_result = sim_out_of_order.vehicles.get(DefaultIds.mock_vehicle_id())
        self.assertIsNotNone(veh_result, "stepped vehicle should have advanced the simulation state")
        self.assertIsInstance(veh_result.vehicle_state, OutOfService,
                              "should have landed in out of service state")
