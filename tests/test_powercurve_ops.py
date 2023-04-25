from unittest import TestCase

from nrel.hive.resources.mock_lobster import mock_bev, mock_vehicle, mock_dcfc_charger
from nrel.hive.model.vehicle.mechatronics.powercurve.powercurve_ops import time_to_full


class TestPowercurveOps(TestCase):
    def test_time_to_full_when_near_full(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0.99)  # ...almost full
        charger = mock_dcfc_charger()

        time_to_full(
            vehicle,
            bev,
            charger,
            target_soc=1.0,
            sim_timestep_duration_seconds=60,
            min_delta_energy_change=0.0001,
            max_iterations=10_000,
        )

    def test_time_to_full_when_near_zero(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0)  # ...almost full
        charger = mock_dcfc_charger()

        time_to_full(
            vehicle,
            bev,
            charger,
            target_soc=1.0,
            sim_timestep_duration_seconds=60,
            min_delta_energy_change=0.0001,
            max_iterations=10_000,
        )

    # @unittest.skip("Skipping stress test of function")
    def test_stress_time_to_full(self):
        bev = mock_bev(battery_capacity_kwh=5000)
        vehicle = mock_vehicle(soc=0)  # ...almost full
        charger = mock_dcfc_charger()

        time_to_full(
            vehicle,
            bev,
            charger,
            target_soc=1.0,
            sim_timestep_duration_seconds=60,
            min_delta_energy_change=0.0001,
            max_iterations=10_000,
        )
