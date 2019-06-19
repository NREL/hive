import os
import sys
import shutil
import pickle
import unittest
import pandas as pd

sys.path.append('../')
from hive import reporting
from hive.utils import initialize_log
from hive.vehicle import Vehicle

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_INPUT_DIR = os.path.join('../', 'inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join(THIS_DIR, '.tmp')

class ReportingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)
        cls.reqs_df = pd.DataFrame({'passengers': [1, 2]})

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_calc_fleet_stats(self):
        vehicle_summary_file = os.path.join(TEST_OUTPUT_DIR, 'vehicle_summary.csv')
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        fleet_summary_file = os.path.join(TEST_OUTPUT_DIR, 'fleet_summary.txt')

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

        initialize_log(veh1._STATS, vehicle_summary_file)

        veh1.dump_stats(vehicle_summary_file)
        veh2.dump_stats(vehicle_summary_file)

        reporting.calc_fleet_stats(fleet_summary_file, vehicle_summary_file, self.reqs_df)

        self.assertTrue(os.path.isfile(vehicle_summary_file))

        #TODO: make test more robust by checking accurate calculations.



if __name__ == "__main__":
    unittest.main()
