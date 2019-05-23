import unittest
import os

from hive.station import FuelStation
from hive.constraints import STATION_PARAMS

TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')

class StationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_station_plug_exception(self):
        with self.assertRaises(Exception) as context:
            station = FuelStation(station_id = 1,
                                    latitude = 0,
                                    longitude = 0,
                                    plugs = -1,
                                    plug_type = "DC",
                                    plug_power = 150,
                                    logfile="placeholder")

        low_limit = STATION_PARAMS['TOTAL_PLUGS'][1]
        expected_error = f"Param TOTAL_PLUGS:-1 is under low limit {low_limit}"

        self.assertTrue(expected_error in str(context.exception))

    def test_station_plug_type_exception(self):
        with self.assertRaises(Exception) as context:
            station = FuelStation(station_id = 1,
                                    latitude = 0,
                                    longitude = 0,
                                    plugs = 1,
                                    plug_type = "XX",
                                    plug_power = 150,
                                    logfile="placeholder")

        expected_error = f"Param PLUG_TYPE:XX must be from set"

        self.assertTrue(expected_error in str(context.exception))

    def test_station_plug_power_exception(self):
        with self.assertRaises(Exception) as context:
            station = FuelStation(station_id = 1,
                                    latitude = 0,
                                    longitude = 0,
                                    plugs = 1,
                                    plug_type = "DC",
                                    plug_power = -1,
                                    logfile="placeholder")

        low_limit = STATION_PARAMS['PLUG_POWER'][1]
        expected_error = f"Param PLUG_POWER:-1 is under low limit {low_limit}"

        self.assertTrue(expected_error in str(context.exception))
