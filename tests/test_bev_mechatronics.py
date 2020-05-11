from unittest import TestCase

from hive.util.units import hours_to_seconds
from tests.mock_lobster import *
from hive.model.energy.energytype import EnergyType


class TestBEV(TestCase):

    def test_leaf_energy_gain_0_soc(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0)

        charged_vehicle = bev.add_energy(vehicle, Charger.DCFC, hours_to_seconds(10))
        self.assertAlmostEqual(
            charged_vehicle.energy[EnergyType.ELECTRIC]/bev.battery_capacity_kwh,
            1,
            places=2
        )

    def test_leaf_energy_gain_full_soc(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=1)

        charged_vehicle = bev.add_energy(vehicle, Charger.DCFC, hours_to_seconds(10))
        self.assertEqual(charged_vehicle.energy[EnergyType.ELECTRIC], 50, "Should be fully charged")

    def test_leaf_energy_gain_low_power(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0)

        charged_vehicle = bev.add_energy(vehicle, Charger.LEVEL_2, hours_to_seconds(0.1))
        self.assertLess(charged_vehicle.energy[EnergyType.ELECTRIC], 50, "Should not be fully charged")

    def test_leaf_energy_cost_empty_route(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=1)

        moved_vehicle = bev.move(vehicle, route=())
        self.assertEqual(moved_vehicle.energy[EnergyType.ELECTRIC], 50, "empty route should yield zero energy cost")

    def test_leaf_energy_cost_real_route(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=1)
        test_route = mock_route(speed_kmph=45)
        moved_vehicle = bev.move(vehicle, route=test_route)
        self.assertLess(moved_vehicle.energy[EnergyType.ELECTRIC], 50, "route should yield some energy cost")
