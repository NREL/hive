import os
import sys
import shutil
import unittest
import csv

sys.path.append('../')
from hive.vehicle import Vehicle
from hive.constraints import VEH_PARAMS
from hive.utils import initialize_log

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_INPUT_DIR = os.path.join('../', 'inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join(THIS_DIR, '.tmp')

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
                            max_passengers = 4,
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
                            max_passengers = 4,
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
                            max_passengers = 4,
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
                            max_passengers = 4,
                            initial_soc = 0.2,
                            whmi_lookup = "placeholder",
                            charge_template = "placeholder",
                            logfile = log_file,
                            environment_params={'BAD_PARAM': 1})

        expected_error= "Got an unexpected parameter BAD_PARAM"

        self.assertTrue(expected_error in str(context.exception))

    def test_vehicle_dump_stats_init(self):
        summary_file = os.path.join(TEST_OUTPUT_DIR, 'vehicle_summary.csv')
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        veh = Vehicle(veh_id = 1,
                        name='test',
                        battery_capacity = 10,
                        max_passengers = 4,
                        initial_soc = 0.2,
                        whmi_lookup = "placeholder",
                        charge_template = "placeholder",
                        logfile = log_file)
        initialize_log(veh._STATS, summary_file)

        veh.dump_stats(summary_file)
        self.assertTrue(os.path.isfile(summary_file))
        with open(summary_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertTrue(header == veh._STATS)

    def test_vehicle_dump_stats_content(self):
        summary_file = os.path.join(TEST_OUTPUT_DIR, 'vehicle_summary.csv')
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        veh1 = Vehicle(veh_id = 1,
                        name='test1',
                        battery_capacity = 10,
                        max_passengers = 4,
                        initial_soc = 0.2,
                        whmi_lookup = "placeholder",
                        charge_template = "placeholder",
                        logfile = log_file)
        veh2 = Vehicle(veh_id = 2,
                        name='test2',
                        battery_capacity = 10,
                        max_passengers = 4,
                        initial_soc = 0.2,
                        whmi_lookup = "placeholder",
                        charge_template = "placeholder",
                        logfile = log_file)
        initialize_log(veh1._STATS, summary_file)

        veh1.dump_stats(summary_file)
        veh2.dump_stats(summary_file)

        with open(summary_file, 'r') as f:
            reader = csv.DictReader(f)
            veh_ids = list()
            for row in reader:
                veh_ids.append(row['veh_id'])

        self.assertTrue('1' in veh_ids)
        self.assertTrue('2' in veh_ids)

if __name__ == "__main__":
    unittest.main()
