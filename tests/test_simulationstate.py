from unittest import TestCase

from hive.state.entity_state import entity_state_ops
from hive.state.simulation_state.update.step_simulation import perform_vehicle_state_updates
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_trip import ServicingTrip
from hive.resources.mock_lobster import *


class TestSimulationState(TestCase):

    def test_at_vehicle_geoid(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sta = mock_station_from_geoid(geoid=somewhere)
        b = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim(
            vehicles=(veh,),
            stations=(sta,),
            bases=(b,)
        )
        sim_with_request = simulation_state_ops.add_request_safe(sim, req).unwrap()

        result = sim_with_request.at_geoid(veh.geoid)
        self.assertIn(veh.id, result['vehicles'], "should have found this vehicle")
        self.assertIn(req.id, result['requests'], "should have found this request")
        self.assertIn(sta.id, result['station'], "should have found this station")
        self.assertEqual(result['base'], frozenset(), "should not have found this base")

    def test_vehicle_at_request(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(vehicles=(veh,))
        sim_with_veh = simulation_state_ops.add_request_safe(sim, req).unwrap()
        result = sim_with_veh.vehicle_at_request(veh.id, req.id)
        self.assertTrue(result, "the vehicle should be at the request")

    def test_vehicle_not_at_request(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else)
        sim = mock_sim(vehicles=(veh,))
        sim_with_veh = simulation_state_ops.add_request_safe(sim, req).unwrap()
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
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)

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
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)

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
            charger_id=mock_dcfc_charger_id()
        )
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)

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
            charger_id=mock_dcfc_charger_id()
        )

        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)

        self.assertIsNone(sim_updated)



    def test_step_charging_vehicle(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.5)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger_id=mock_dcfc_charger_id()
        )

        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        sim_charging_veh = perform_vehicle_state_updates(sim_updated, env)

        charged_veh = sim_charging_veh.vehicles[veh.id]

        self.assertGreater(charged_veh.energy[EnergyType.ELECTRIC],
                           veh.energy[EnergyType.ELECTRIC],
                           "Vehicle should have gained energy")

    def test_step_idle_vehicle(self):
        veh = mock_vehicle_from_geoid()
        sim = mock_sim(vehicles=(veh,))
        env = mock_env()

        sim_idle_veh = perform_vehicle_state_updates(sim, env)

        idle_veh = sim_idle_veh.vehicles[veh.id]

        self.assertLess(idle_veh.energy[EnergyType.ELECTRIC],
                        veh.energy[EnergyType.ELECTRIC],
                        "Idle vehicle should have consumed energy")


    def test_terminal_state_starting_trip(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        req = mock_request_from_geoids(origin=somewhere_else,
                                       destination=somewhere,
                                       passengers=2)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(veh,)), req).unwrap()

        instruction = DispatchTripInstruction(vehicle_id=veh.id, request_id=req.id)
        env = mock_env()
        e2, instruction_result = instruction.apply_instruction(sim, env)
        if e2:
            self.fail(e2.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # should take about 17 seconds to arrive at trip origin, and
        # 1 more state step of any size to transition state

        sim_at_req = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=20), env)
        sim_with_req = perform_vehicle_state_updates(sim_at_req._replace(sim_timestep_duration_seconds=1), env)

        tripping_veh = sim_with_req.vehicles[veh.id]

        self.assertIsInstance(tripping_veh.vehicle_state, ServicingTrip)

        # should take about 17 seconds to arrive at trip destination
        # we take 1 small time step crank afterward to find we are in our terminal condition -> Idle
        sim_dropoff = perform_vehicle_state_updates(sim_with_req._replace(sim_timestep_duration_seconds=20), env)
        sim_idle = perform_vehicle_state_updates(sim_dropoff._replace(sim_timestep_duration_seconds=1), env)

        idle_veh = sim_idle.vehicles[veh.id]

        self.assertIsInstance(idle_veh.vehicle_state, Idle, "Vehicle should have transitioned to idle.")
        self.assertEqual(idle_veh.geoid, req.destination, "Vehicle should be at request destination.")
        self.assertEqual(req.id not in sim_idle.requests, True, "Request should have been removed from simulation.")

    def test_terminal_state_dispatch_station(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.5)
        sta = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))
        env = mock_env()

        instruction = DispatchStationInstruction(vehicle_id=veh.id, station_id=sta.id, charger_id=mock_dcfc_charger_id())
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        sim_at_sta = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_sta = perform_vehicle_state_updates(sim_at_sta._replace(sim_timestep_duration_seconds=1), env)

        charging_veh = sim_in_sta.vehicles[veh.id]
        station_w_veh = sim_in_sta.stations[sta.id]

        self.assertIsInstance(charging_veh.vehicle_state,
                              ChargingStation,
                              "Vehicle should have transitioned to charging.")
        self.assertEqual(charging_veh.geoid, sta.geoid, "Vehicle should be at station.")
        self.assertLess(station_w_veh.get_available_chargers(mock_dcfc_charger_id()),
                        station_w_veh.get_total_chargers(mock_dcfc_charger_id()),
                        "Station should have charger_id in use.")

    def test_terminal_state_dispatch_base(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        veh = mock_vehicle_from_geoid(geoid=somewhere)
        base = mock_base_from_geoid(base_id='b1', geoid=somewhere_else)
        sim = mock_sim(vehicles=(veh,), bases=(base,))
        env = mock_env()

        instruction = DispatchBaseInstruction(vehicle_id=veh.id, base_id=base.id)
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        self.assertIsNotNone(sim, "Vehicle should have set instruction.")

        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_base = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_base = perform_vehicle_state_updates(sim_at_base._replace(sim_timestep_duration_seconds=1), env)

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
        somewhere_else_link = sim.road_network.position_from_geoid(somewhere_else)

        instruction = RepositionInstruction(vehicle_id=veh.id, destination=somewhere_else_link.link_id)
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        # 1000 seconds should get us there, and 1 more sim step of any size to transition vehicle state
        sim_at_new_pos = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=1000), env)
        sim_in_new_state = perform_vehicle_state_updates(sim_at_new_pos._replace(sim_timestep_duration_seconds=1), env)

        veh_at_new_loc = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(veh_at_new_loc.vehicle_state,
                              Idle,
                              "Vehicle should have transitioned to IDLE")
        self.assertEqual(veh_at_new_loc.geoid,
                         somewhere_else,
                         "Vehicle should be located at somewhere_else")

    def test_terminal_state_charging(self):
        sta = mock_station_from_geoid()
        veh = mock_vehicle_from_geoid(soc=0.75)
        sim = mock_sim(vehicles=(veh,), stations=(sta,))

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger_id=mock_dcfc_charger_id()
        )
        env = mock_env()
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        # 10 hours should get us charged , and 1 more sim step of any size to transition vehicle state
        sim_charged = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=36000), env)
        sim_in_new_state = perform_vehicle_state_updates(sim_charged._replace(sim_timestep_duration_seconds=1), env)

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(fully_charged_veh.vehicle_state,
                              Idle,
                              "Vehicle should have transitioned to IDLE")

    def test_terminal_state_charging_base(self):
        veh = mock_vehicle_from_geoid(soc=0.75)
        sta = mock_station_from_geoid()
        bas = mock_base_from_geoid(station_id=sta.id)
        sim = mock_sim(vehicles=(veh,), stations=(sta,), bases=(bas,))

        instruction = ChargeBaseInstruction(
            vehicle_id=veh.id,
            base_id=bas.id,
            charger_id=mock_dcfc_charger_id()
        )
        env = mock_env()
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)

        self.assertIsNotNone(sim, "Vehicle should have set instruction.")
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        # 10 hours should get us charged, and 1 more sim step of any size to transition vehicle state
        sim_charged = perform_vehicle_state_updates(sim_updated._replace(sim_timestep_duration_seconds=36000), env)
        sim_in_new_state = perform_vehicle_state_updates(sim_charged._replace(sim_timestep_duration_seconds=1), env)

        fully_charged_veh = sim_in_new_state.vehicles[veh.id]

        self.assertIsInstance(fully_charged_veh.vehicle_state,
                              ReserveBase,
                              "Vehicle should have transitioned to RESERVE_BASE")

    def test_vehicle_runs_out_of_energy(self):

        low_energy_veh = mock_vehicle_from_geoid(soc=0.01)
        sim = mock_sim(vehicles=(low_energy_veh,), sim_timestep_duration_seconds=3600)

        env = mock_env()

        inbox_cafe_in_torvet_julianehab_greenland = h3.geo_to_h3(63.8002568, -53.3170783, 15)
        dst_link = sim.road_network.position_from_geoid(inbox_cafe_in_torvet_julianehab_greenland)
        instruction = RepositionInstruction(DefaultIds.mock_vehicle_id(), dst_link.link_id)
        error, instruction_result = instruction.apply_instruction(sim, env)
        if error:
            self.fail(error.args)
        sim_error, sim_updated = entity_state_ops.transition_previous_to_next(sim, env, instruction_result.prev_state, instruction_result.next_state)
        self.assertIsNotNone(sim_updated, "test invariant failed - should be able to reposition default vehicle")

        # one movement takes more energy than this agent has
        sim_out_of_order = perform_vehicle_state_updates(sim_updated, env)

        veh_result = sim_out_of_order.vehicles.get(DefaultIds.mock_vehicle_id())
        self.assertIsNotNone(veh_result, "stepped vehicle should have advanced the simulation state")
        self.assertIsInstance(veh_result.vehicle_state, OutOfService,
                              "should have landed in out of service state")

    def test_get_stations(self):
        sim = mock_sim(stations=(
            mock_station('s1', lat=0, lon=0, chargers=immutables.Map({mock_dcfc_charger_id(): 1}, )),
            mock_station('s2', lat=1, lon=1, chargers=immutables.Map({mock_l2_charger_id(): 1}, )),
        ))

        def has_dcfc(station: Station) -> bool:
            return station.has_available_charger(mock_dcfc_charger_id())

        dcfc_stations = sim.get_stations(filter_function=has_dcfc)

        self.assertEqual(len(dcfc_stations), 1, 'only one station with dcfc charger_id')
        self.assertEqual(dcfc_stations[0].id, 's1', 's1 has dcfc charger_id')

    def test_get_stations_at_same_geoid(self):
        sim = mock_sim(stations=(
            mock_station('s1', lat=0, lon=0, chargers=immutables.Map({mock_dcfc_charger_id(): 1}, )),
            mock_station('s2', lat=0, lon=0, chargers=immutables.Map({mock_l2_charger_id(): 1}, )),
        ))

        geoid = h3.geo_to_h3(0, 0, sim.sim_h3_location_resolution)

        stations = sim.s_locations[geoid]

        self.assertIn('s1', stations, "station s1 should be at this geoid")
        self.assertIn('s2', stations, "station s2 should be at this geoid")

    def test_get_bases(self):
        sim = mock_sim(bases=(
            mock_base('b1', lat=0, lon=0, stall_count=0),
            mock_base('b2', lat=1, lon=1, stall_count=2),
            mock_base('b3', lat=2, lon=2, stall_count=1),
        ))

        sorted_bases = sim.get_bases(sort=True, sort_reversed=True, sort_key=lambda b: b.total_stalls)

        self.assertEqual(sorted_bases[0].id, 'b2', 'base 2 has the most stalls')

    def test_get_bases_at_same_geoid(self):
        sim = mock_sim(bases=(
            mock_base('b1', lat=0, lon=0, stall_count=0),
            mock_base('b2', lat=0, lon=0, stall_count=2),
        ))

        geoid = h3.geo_to_h3(0, 0, sim.sim_h3_location_resolution)

        bases = sim.b_locations[geoid]

        self.assertIn('b1', bases, "base b1 should be at this geoid")
        self.assertIn('b2', bases, "base b2 should be at this geoid")

    def test_get_vehicles(self):
        sim = mock_sim(vehicles=(
            mock_vehicle('v1', soc=1),
            mock_vehicle('v2', soc=0.5),
            mock_vehicle('v3', soc=0.2),
            mock_vehicle('v4', soc=0.1),
        ))

        sorted_and_filtered_vehicles = sim.get_vehicles(
            sort=True,
            sort_key=lambda v: v.energy[EnergyType.ELECTRIC],
            sort_reversed=True,
        )

        self.assertEqual(sorted_and_filtered_vehicles[0].id, 'v1', 'v1 has highest soc')

    def test_get_requests(self):
        sim = mock_sim()
        r1 = mock_request('r1', departure_time=0)
        r2 = mock_request('r2', departure_time=10)
        r3 = mock_request('r3', departure_time=20)
        sim = simulation_state_ops.add_request_safe(sim, r3).unwrap()
        sim = simulation_state_ops.add_request_safe(sim, r2).unwrap()
        sim = simulation_state_ops.add_request_safe(sim, r1).unwrap()

        sorted_requests = sim.get_requests(sort=True, sort_key=lambda r: r.departure_time)

        self.assertEqual(sorted_requests[0].id, 'r1', 'r1 has lowest departure time')

