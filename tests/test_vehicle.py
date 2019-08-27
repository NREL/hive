import os
import sys
import unittest

from build_test_env import setup_env

sys.path.append('../')
from hive.vehicle import Vehicle

class VehicleTest(unittest.TestCase):
    def setUp(self):
        self.SIM_ENV = setup_env()

    def tearDown(self):
        pass

    def test_vehicle_cmd_make_trip(self):
        self.assertTrue(True == False)


if __name__ == "__main__":
    unittest.main()
