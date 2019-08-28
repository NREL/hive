import os
import sys
import shutil
import unittest
from datetime import datetime

from build_test_env import load_test_scenario

sys.path.append('../')
from hive.initialize import initialize_stations
from hive.utils import Clock
from hive.units import SECONDS_TO_HOURS


class StationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.TIMESTEP_S = 60
        data = load_test_scenario()
        cls.stations = initialize_stations(data['stations'], clock=Clock(cls.TIMESTEP_S))

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_station_dispense_energy(self):
        test_station = self.stations[0]
        test_station.PLUG_POWER_KW = 50
        expected_energy_kwh = test_station.PLUG_POWER_KW * (self.TIMESTEP_S * SECONDS_TO_HOURS)
        station_energy_kwh = test_station.dispense_energy()
        self.assertTrue(expected_energy_kwh == station_energy_kwh)



if __name__ == "__main__":
    unittest.main()
