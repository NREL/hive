from unittest import TestCase

from tests.mock_lobster import *


class TestManagedDispatcher(TestCase):
    def test_match_vehicle(self):
        dispatcher = mock_dispatcher()

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        near_to_somewhere = h3.geo_to_h3(39.754, -104.975, 15)
        far_from_somewhere = h3.geo_to_h3(39.755, -104.976, 15)

        req = mock_request_from_geoids(origin=somewhere)
        close_veh = mock_vehicle_from_geoid(vehicle_id='close_veh', geoid=near_to_somewhere)
        far_veh = mock_vehicle_from_geoid(vehicle_id='far_veh', geoid=far_from_somewhere)
        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(close_veh, far_veh),
        )
        _, sim = simulation_state_ops.add_request(sim, req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[close_veh.id],
                              DispatchTripInstruction,
                              "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions_map[close_veh.id].vehicle_id,
                         close_veh.id,
                         "Should have picked closest vehicle")

    def test_no_vehicles(self):
        dispatcher = mock_dispatcher()

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9)
        _, sim = simulation_state_ops.add_request(sim, req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions_map), 0, "There are no vehicles to make assignments to.")

    def test_charge_vehicle(self):
        dispatcher = mock_dispatcher()

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        low_battery = mock_energy_source(soc=0.1)

        veh_low_battery = veh.modify_energy_source(low_battery)
        station = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(h3_location_res=9, h3_search_res=9, vehicles=(veh_low_battery,), stations=(station,))

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh.id],
                              DispatchStationInstruction,
                              "Should have instructed vehicle to dispatch to station")

    def test_activate_vehicles(self):
        dispatcher = mock_dispatcher()

        # manger will always predict we need 1 activate vehicle. So, we start with one inactive vehicle and see
        # if it is moved to active.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)

        veh = mock_vehicle_from_geoid(
            geoid=somewhere,
            vehicle_state=ReserveBase(
                DefaultIds.mock_vehicle_id(),
                DefaultIds.mock_base_id()
            )
        )
        base = mock_base_from_geoid(geoid=somewhere, stall_count=2)

        sim = mock_sim(vehicles=(veh,), bases=(base,))

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh.id],
                              RepositionInstruction,
                              "Should have instructed vehicle to reposition")

    def test_deactivate_vehicles(self):
        dispatcher = mock_dispatcher()

        # manger will always predict we need 1 activate vehicle. So, we start with two active vehicle and see
        # if it is moved to base.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh1 = mock_vehicle_from_geoid(vehicle_id='v1', geoid=somewhere)
        veh2 = mock_vehicle_from_geoid(vehicle_id='v2', geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere_else, stall_count=2)

        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(veh1, veh2),
            bases=(base,)
        )

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions_map), 1, "Should have generated only one instruction")
        self.assertIsInstance(list(instructions_map.values())[0],
                              DispatchBaseInstruction,
                              "Should have instructed vehicle to dispatch to base")

    def test_valuable_requests(self):
        dispatcher = mock_dispatcher()

        # manger will always predict we need 1 activate vehicle. So, we start with two active vehicle and see
        # if it is moved to base.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh1 = mock_vehicle_from_geoid(vehicle_id='v1', geoid=somewhere)
        expensive_req = mock_request_from_geoids(request_id='expensive', origin=somewhere_else, value=100)
        cheap_req = mock_request_from_geoids(request_id='cheap', origin=somewhere_else, value=10)

        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(veh1,)
        )
        _, sim = simulation_state_ops.add_request(sim, expensive_req)
        _, sim = simulation_state_ops.add_request(sim, cheap_req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh1.id],
                              DispatchTripInstruction,
                              "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions_map[veh1.id].request_id, 'expensive', 'Should have picked expensive request')
