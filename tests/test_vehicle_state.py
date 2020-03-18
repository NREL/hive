from unittest import TestCase

from hive.model.vehicle.vehicle_state.charging import Charging
from tests.mock_lobster import *


class TestVehicleState(TestCase):

    def test_charging_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle, ),
            stations=(station, )
        )
        env = mock_env()

        state = Charging(vehicle.id, station.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, Charging, "should be in a charging state")
        self.assertEquals(available_chargers, 0, "should have claimed the only DCFC charger")

    def test_charging_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle, ),
            stations=(station, )
        )
        env = mock_env()

        state = Charging(vehicle.id, station.id, charger)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.exit(updated_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, Charging, "should still be in a charging state")
        self.assertEquals(available_chargers, 1, "should have returned the only DCFC charger")

    def test_charging_update(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle, ),
            stations=(station, )
        )
        env = mock_env()

        state = Charging(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertAlmostEqual(
            first=updated_vehicle.energy_source.energy_kwh,
            second=vehicle.energy_source.energy_kwh + 0.83,
            places=2,
            msg="should have charged for 60 seconds")

    def test_charging_update_terminal(self):
        vehicle = mock_vehicle(soc=0.99)
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = Charging(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "vehicle should be in idle state")

    def test_charging_update_terminal_at_base(self):
        vehicle = mock_vehicle(soc=0.99)
        station, base = mock_station(), mock_base()  # invariant: should be co-located
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = Charging(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ReserveBase, "vehicle should be in idle state")