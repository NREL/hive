from unittest import TestCase

from nrel.hive.resources.mock_lobster import mock_bev, mock_vehicle, mock_dcfc_charger
from nrel.hive.model.vehicle.mechatronics.powercurve.powercurve_ops import time_to_full


class TestPowercurveOps(TestCase):
    def test_time_to_fill(self):
        bev = mock_bev(battery_capacity_kwh=50)
        vehicle = mock_vehicle(soc=0.99)  # ...almost full
        charger = mock_dcfc_charger()

        time_to_full(vehicle, bev, charger, target_soc=1.0, sim_timestep_duration_seconds=60)



