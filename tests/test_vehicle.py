import unittest
import os
import shutil

from hive.vehicle import Vehicle
from hive.constraints import VEH_PARAMS

TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join('tests', '.tmp')

class VehicleTest(unittest.TestCase):
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

    def test_vehicle_battery_exception(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        with self.assertRaises(Exception) as context:
            veh = Vehicle(veh_id = 1,
                            name='test',
                            battery_capacity = -1,
                            initial_soc = 0.2,
                            whmi_lookup = "placeholder",
                            charge_template = "placeholder",
                            logfile = log_file)

        low_limit = VEH_PARAMS['BATTERY_CAPACITY'][1]
        expected_error = f"Param BATTERY_CAPACITY:-1 is under low limit {low_limit}"

        self.assertTrue(expected_error in str(context.exception))

    def test_vehicle_soc_exception_low(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        with self.assertRaises(Exception) as context:
            veh = Vehicle(veh_id = 1,
                            name='test',
                            battery_capacity = 10,
                            initial_soc = -0.1,
                            whmi_lookup = "placeholder",
                            charge_template = "placeholder",
                            logfile = log_file)

        low_limit = VEH_PARAMS['INITIAL_SOC'][1]
        expected_error = f"Param INITIAL_SOC:-0.1 is under low limit {low_limit}"

        self.assertTrue(expected_error in str(context.exception))

    def test_vehicle_soc_exception_high(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        with self.assertRaises(Exception) as context:
            veh = Vehicle(veh_id = 1,
                            name='test',
                            battery_capacity = 10,
                            initial_soc = 1.2,
                            whmi_lookup = "placeholder",
                            charge_template = "placeholder",
                            logfile = log_file)

        high_limit = VEH_PARAMS['INITIAL_SOC'][2]
        expected_error = f"Param INITIAL_SOC:1.2 is over high limit {high_limit}"

        self.assertTrue(expected_error in str(context.exception))

    def test_vehicle_bad_env_param(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        with self.assertRaises(Exception) as context:
            veh = Vehicle(veh_id = 1,
                            name='test',
                            battery_capacity = 10,
                            initial_soc = 0.2,
                            whmi_lookup = "placeholder",
                            charge_template = "placeholder",
                            logfile = log_file,
                            environment_params={'BAD_PARAM': 1})

        expected_error= "Got an unexpected parameter BAD_PARAM"

        self.assertTrue(expected_error in str(context.exception))
