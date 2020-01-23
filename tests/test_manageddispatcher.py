from unittest import TestCase

from hive.dispatcher.managed_dispatcher import ManagedDispatcher
from hive.model.instruction import *
from tests.mock_lobster import *


class TestManagedDispatcher(TestCase):

    def test_match_vehicle(self):
        manager = mock_manager(forecaster=mock_forecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file='downtown_denver.geojson',
        )

        # h3 resolution = 9
        somewhere = '89283470d93ffff'
        close_to_somewhere = '89283470d87ffff'
        far_from_somewhere = '89283470c27ffff'

        req = mock_request_from_geoids(origin=somewhere)
        close_veh = mock_vehicle_from_geoid(vehicle_id='close_veh', geoid=close_to_somewhere)
        far_veh = mock_vehicle_from_geoid(vehicle_id='far_veh', geoid=far_from_somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_request(req).add_vehicle(close_veh).add_vehicle(far_veh)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions[0],
                              DispatchTripInstruction,
                              "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions[0].vehicle_id,
                         close_veh.id,
                         "Should have picked closest vehicle")

    def test_no_vehicles(self):
        manager = mock_manager(forecaster=mock_forecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file='downtown_denver.geojson',
        )

        # h3 resolution = 9
        somewhere = '89283470d93ffff'

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_request(req)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions), 0, "There are no vehicles to make assignments to.")

    def test_charge_vehicle(self):
        manager = mock_manager(forecaster=mock_forecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file='downtown_denver.geojson',
        )

        # h3 resolution = 9
        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        low_battery = mock_energy_source(soc=0.1)

        veh_low_battery = veh.battery_swap(low_battery)
        station = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_vehicle(veh_low_battery).add_station(station)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions[0],
                              DispatchStationInstruction,
                              "Should have instructed vehicle to dispatch to station")


    def test_activate_vehicles(self):
        manager = mock_manager(forecaster=mock_forecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file='downtown_denver.geojson',
        )

        # manger will always predict we need 1 activate vehicle. So, we start with one inactive vehicle and see
        # if it is moved to active.

        somewhere = '89283470d93ffff'

        veh = mock_vehicle_from_geoid(geoid=somewhere).transition(VehicleState.RESERVE_BASE)
        base = mock_base_from_geoid(geoid=somewhere, stall_count=2)

        sim = mock_sim().add_vehicle(veh).add_base(base)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions[0],
                              RepositionInstruction,
                              "Should have instructed vehicle to reposition")

    def test_deactivate_vehicles(self):
        manager = mock_manager(forecaster=mock_forecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file='downtown_denver.geojson',
        )

        # manger will always predict we need 1 activate vehicle. So, we start with two active vehicle and see
        # if it is moved to base.

        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh1 = mock_vehicle_from_geoid(vehicle_id='v1', geoid=somewhere)
        veh2 = mock_vehicle_from_geoid(vehicle_id='v2', geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere_else, stall_count=2)

        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_vehicle(veh1).add_vehicle(veh2).add_base(base)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        print(instructions)

        self.assertEqual(len(instructions), 1, "Should have generated only one instruction")
        self.assertIsInstance(instructions[0],
                              DispatchBaseInstruction,
                              "Should have instructed vehicle to dispatch to base")

