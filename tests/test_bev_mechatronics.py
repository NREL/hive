from unittest import TestCase

from hive.resources.mock_lobster import *


class TestBEV(TestCase):

    def test_leaf_energy_gain_0_soc(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0)

        charged_vehicle, _ = bev.add_energy(vehicle, mock_dcfc_charger(), hours_to_seconds(10))
        self.assertAlmostEqual(
            charged_vehicle.energy[EnergyType.ELECTRIC] / bev.battery_capacity_kwh,
            1,
            places=2
        )

    def test_leaf_energy_gain_full_soc(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=1)

        charged_vehicle, _ = bev.add_energy(vehicle, mock_dcfc_charger(), hours_to_seconds(10))
        self.assertEqual(charged_vehicle.energy[EnergyType.ELECTRIC], 50, "Should be fully charged")

    def test_leaf_energy_gain_low_power(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0)

        charged_vehicle, _ = bev.add_energy(vehicle, mock_l2_charger(), hours_to_seconds(0.1))
        self.assertLess(charged_vehicle.energy[EnergyType.ELECTRIC], 50, "Should not be fully charged")

    def test_leaf_energy_cost_empty_route(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=1)

        moved_vehicle = bev.consume_energy(vehicle, route=())
        self.assertEqual(moved_vehicle.energy[EnergyType.ELECTRIC], 50, "empty route should yield zero energy cost")

    def test_leaf_energy_cost_real_route(self):
        bev = mock_bev(battery_capacity_kwh=50, nominal_watt_hour_per_mile=1000)
        vehicle = mock_vehicle(soc=1)

        # route is ~ 3km in length
        test_route = mock_route(speed_kmph=45)

        expected_energy_kwh = vehicle.energy[EnergyType.ELECTRIC] - 1 * (3 * KM_TO_MILE)

        moved_vehicle = bev.consume_energy(vehicle, route=test_route)
        self.assertAlmostEqual(
            moved_vehicle.energy[EnergyType.ELECTRIC],
            expected_energy_kwh,
            places=0)

    def test_remaining_range(self):
        bev = mock_bev(battery_capacity_kwh=50, nominal_watt_hour_per_mile=1000)
        vehicle = mock_vehicle(soc=1)

        remaining_range_km = bev.range_remaining_km(vehicle)

        self.assertAlmostEqual(
            remaining_range_km,
            50 * MILE_TO_KM,
            places=1,
        )

    def test_calc_required_soc(self):
        bev = mock_bev(battery_capacity_kwh=50, nominal_watt_hour_per_mile=1000)

        required_soc = bev.calc_required_soc(50 * MILE_TO_KM)

        self.assertEqual(
            required_soc,
            1.0,
        )
