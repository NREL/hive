from unittest import TestCase

from hive.resources.mock_lobster import *


class TestICE(TestCase):

    def test_energy_gain(self):
        ice = mock_ice(tank_capacity_gallons=10)
        vehicle = mock_vehicle(soc=0, mechatronics=ice)

        full_vehicle, _ = ice.add_energy(vehicle, mock_gasoline_pump(), hours_to_seconds(10))
        self.assertAlmostEqual(
            full_vehicle.energy[EnergyType.GASOLINE] / ice.tank_capacity_gallons,
            1,
            places=2
        )

    def test_energy_gain_full_soc(self):
        ice = mock_ice(tank_capacity_gallons=10)
        vehicle = mock_vehicle(soc=1, mechatronics=ice)

        full_vehicle, _ = ice.add_energy(vehicle, mock_gasoline_pump(), hours_to_seconds(10))

        self.assertEqual(full_vehicle.energy[EnergyType.GASOLINE], 10, "Should be full")

    def test_energy_cost_empty_route(self):
        ice = mock_ice(tank_capacity_gallons=10)
        vehicle = mock_vehicle(soc=1, mechatronics=ice)

        moved_vehicle = ice.consume_energy(vehicle, route=())
        self.assertEqual(moved_vehicle.energy[EnergyType.GASOLINE], 10, "empty route should yield zero energy cost")

    def test_energy_cost_real_route(self):
        ice = mock_ice(tank_capacity_gallons=10, nominal_miles_per_gallon=10)
        vehicle = mock_vehicle(soc=1, mechatronics=ice)

        # route is ~ 3km in length
        test_route = mock_route()

        expected_gal_gas = 3 * KM_TO_MILE / 10

        moved_vehicle = ice.consume_energy(vehicle, route=test_route)
        self.assertAlmostEqual(
            10 - moved_vehicle.energy[EnergyType.GASOLINE],
            expected_gal_gas,
            places=0)

    def test_remaining_range(self):
        ice = mock_ice(tank_capacity_gallons=10, nominal_miles_per_gallon=10)
        vehicle = mock_vehicle(soc=1, mechatronics=ice)

        remaining_range_km = ice.range_remaining_km(vehicle)

        self.assertAlmostEqual(
            remaining_range_km,
            100 * MILE_TO_KM,
            places=1,
        )

    def test_calc_required_soc(self):
        ice = mock_ice(tank_capacity_gallons=10, nominal_miles_per_gallon=10)

        required_tank_capacity = ice.calc_required_soc(100 * MILE_TO_KM)

        self.assertEqual(
            required_tank_capacity,
            1.0,
        )
