import unittest
import os
import shutil
from datetime import datetime

from hive.station import FuelStation
from hive.vehicle import Vehicle
from hive.constraints import STATION_PARAMS

TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join('tests', '.tmp')

class StationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

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

    def test_station_add_charge_event(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'test_station_log.csv')
        station = FuelStation(station_id = 1,
                                latitude = 0,
                                longitude = 0,
                                plugs = 1,
                                plug_type = "DC",
                                plug_power = 150,
                                logfile=log_file)
        veh = Vehicle(veh_id = 1,
                        name='test_veh',
                        battery_capacity = 100,
                        initial_soc = 0.5,
                        whmi_lookup = "placeholder",
                        charge_template = "placeholder",
                        logfile = "placeholder")

        start_time = datetime(2019,5,1,1)
        end_time = datetime(2019,5,1,2)
        soc_i = 0.5
        soc_f = 1

        station.add_charge_event(veh, start_time, end_time, soc_i, soc_f)

        self.assertEqual(station.stats['charge_cnt'], 1)
