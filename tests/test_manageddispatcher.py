from unittest import TestCase

from hive.dispatcher.managed_dispatcher import ManagedDispatcher
from hive.dispatcher.forecaster.basic_forecaster import BasicForecaster
from hive.dispatcher.manager.basic_manager import BasicManager
from hive.model.vehiclestate import VehicleState
from tests.mock_lobster import *


class TestManagedDispatcher(TestCase):

    def test_match_vehicle(self):
        forecaster = BasicForecaster()
        manager = BasicManager(demand_forecaster=forecaster)
        dispatcher = ManagedDispatcher(manager=manager)

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
        forecaster = BasicForecaster()
        manager = BasicManager(demand_forecaster=forecaster)
        dispatcher = ManagedDispatcher(manager=manager)

        # h3 resolution = 9
        somewhere = '89283470d93ffff'

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim().add_request(req)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions), 0, "There are no vehicles to make assignments to.")

    def test_charge_vehicle(self):
        forecaster = BasicForecaster()
        manager = BasicManager(demand_forecaster=forecaster)
        dispatcher = ManagedDispatcher(manager=manager)

        # h3 resolution = 9
        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        low_battery = EnergySource.build(
            DefaultIds.mock_powercurve_id(),
            EnergyType.ELECTRIC,
            50*unit.kilowatthour,
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



