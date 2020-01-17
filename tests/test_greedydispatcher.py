from unittest import TestCase

from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from tests.mock_lobster import *


class TestGreedyDispatcher(TestCase):

    def test_match_vehicle(self):
        dispatcher = GreedyDispatcher()

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
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_TRIP,
                         "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions[0].vehicle_id,
                         close_veh.id,
                         "Should have picked closest vehicle")

    def test_no_vehicles(self):
        dispatcher = GreedyDispatcher()

        # h3 resolution = 9
        somewhere = '89283470d93ffff'

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_request(req)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions), 0, "There are no vehicles to make assignments to.")

    def test_charge_vehicle(self):
        dispatcher = GreedyDispatcher()

        # h3 resolution = 9
        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        low_battery = EnergySource.build(
            DefaultIds.mock_powercurve_id(),
            EnergyType.ELECTRIC,
            50,
            soc=0.1
        )

        veh_low_battery = veh.battery_swap(low_battery)
        station = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_vehicle(veh_low_battery).add_station(station)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions), 1, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_STATION,
                         "Should have instructed vehicle to dispatch to station")
        self.assertEqual(instructions[0].location,
                         station.geoid,
                         "Should have picked location equal to test_station")

    def test_charge_vehicle_base(self):
        dispatcher = GreedyDispatcher()

        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = mock_vehicle_from_geoid(vehicle_id='test_veh', geoid=somewhere)\
            .transition(VehicleState.RESERVE_BASE)
        med_battery = EnergySource.build("", EnergyType.ELECTRIC, 50, soc=0.7)
        veh_med_battery = veh.battery_swap(med_battery)
        station = mock_station_from_geoid(station_id='test_station', geoid=somewhere_else)
        base = mock_base_from_geoid(geoid=somewhere, station_id=station.id)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_vehicle(veh_med_battery).add_station(station).add_base(base)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions), 1, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.CHARGING_BASE,
                         "Should have instructed vehicle to charge at base")
        self.assertEqual(instructions[0].station_id,
                         station.id,
                         "Should have picked station_id equal to test_station.id")

    def test_idle_time_out(self):
        dispatcher = GreedyDispatcher()

        # h3 resolution = 9
        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        stationary_vehicle = veh._replace(idle_time_seconds=1000)
        base = mock_base_from_geoid(geoid=somewhere_else)
        sim = mock_sim(h3_location_res=9, h3_search_res=9).add_vehicle(stationary_vehicle).add_base(base)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertIsNotNone(instructions, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_BASE,
                         "Should have instructed vehicle to dispatch to base")
        self.assertEqual(instructions[0].location,
                         base.geoid,
                         "Should have picked location equal to test_station")

