import os
import sys
import shutil
import unittest
from datetime import datetime

from build_test_env import setup_env

sys.path.append('../')
from hive.initialize import initialize_stations
from hive.utils import Clock
from hive.units import SECONDS_TO_HOURS


class StationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SIM_ENV = setup_env()
        cls.stations = SIM_ENV['stations']

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
        timestep_s = test_station._clock.TIMESTEP_S
        expected_energy_kwh = test_station.PLUG_POWER_KW * (timestep_s * SECONDS_TO_HOURS)
        station_energy_kwh = test_station.dispense_energy()
        self.assertTrue(expected_energy_kwh == station_energy_kwh)



if __name__ == "__main__":
    unittest.main()
