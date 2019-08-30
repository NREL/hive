import os
import sys
import shutil
import random
import unittest
import pandas as pd
from numpy import nan

sys.path.append('../')
from hive.preprocess import gen_synth_pax_cnt, load_requests, filter_nulls, \
filter_short_distance_trips, filter_requests_outside_oper_area, \
calculate_road_vmt_scaling_factor, calculate_average_driving_speed

DEFAULT_INPUT_DIR = os.path.join('..', 'inputs', 'library')
TEST_INPUT_DIR = '.tmp'

class PreProcessingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.DEFAULT_REQUESTS_FILE = os.path.join(DEFAULT_INPUT_DIR,
                                                 'requests',
                                                 'aus_2017-02-01.csv')
        cls.NYC_REQUESTS_FILE = os.path.join(DEFAULT_INPUT_DIR,
                                             'requests',
                                             'nyc_2013-03-01_8-12.csv')
        cls.AUSTIN_OPERATING_AREA = os.path.join(DEFAULT_INPUT_DIR,
                                                'operating_area',
                                                'austin_ua.json')
        cls.MANHATTAN_OPERATING_AREA = os.path.join(DEFAULT_INPUT_DIR,
                                                    'operating_area',
                                                    'manhattan.json')

        if not os.path.isdir(TEST_INPUT_DIR):
            os.makedirs(TEST_INPUT_DIR)

        cls.GOOD_TEST_REQUESTS_FILE = os.path.join(TEST_INPUT_DIR,
                                                   'good_requests.csv')
        temp_df = pd.read_csv(cls.DEFAULT_REQUESTS_FILE, nrows=20)
        temp_df.to_csv(cls.GOOD_TEST_REQUESTS_FILE, index=False)

        cls.MISSING_COL_REQUESTS_FILE = os.path.join(TEST_INPUT_DIR,
                                                     'bad_requests_missing_col.csv')
        temp_df = pd.read_csv(cls.GOOD_TEST_REQUESTS_FILE)
        temp_df.drop(columns='pickup_time', inplace=True)
        temp_df.to_csv(cls.MISSING_COL_REQUESTS_FILE, index=False)

        cls.UNEXPECTED_DTYPE_REQUESTS_FILE = os.path.join(TEST_INPUT_DIR,
                                                          'bad_requests_unexpected_dtype.csv')
        temp_df = pd.read_csv(cls.GOOD_TEST_REQUESTS_FILE)
        temp_df['distance_miles'] = 'Not a number'
        temp_df.to_csv(cls.UNEXPECTED_DTYPE_REQUESTS_FILE, index=False)

        cls.CONTAINS_NULLS_REQUESTS_FILE = os.path.join(TEST_INPUT_DIR,
                                                        'requests_contains_nulls.csv')
        temp_df = pd.read_csv(cls.GOOD_TEST_REQUESTS_FILE)
        exp_cols = ['pickup_time',
                    'dropoff_time',
                    'distance_miles',
                    'pickup_lat',
                    'pickup_lon',
                    'dropoff_lat',
                    'dropoff_lon',
                    'passengers']
        null_row = pd.Series([nan]*8, index=exp_cols)
        temp_df = temp_df.append(null_row, ignore_index=True)
        temp_df.to_csv(cls.CONTAINS_NULLS_REQUESTS_FILE, index=False)

        cls.TEST_NYC_REQUESTS_FILE = os.path.join(TEST_INPUT_DIR,
                                                  'nyc_requests.csv')
        temp_df = pd.read_csv(cls.NYC_REQUESTS_FILE, nrows=1500)
        temp_df.to_csv(cls.TEST_NYC_REQUESTS_FILE, index=False)


    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_INPUT_DIR):
            shutil.rmtree(TEST_INPUT_DIR)


    def test_gen_synth_pax_cnt(self):
        random.seed(123)
        synth_pax_cnts = [gen_synth_pax_cnt() for i in range(1000)]
        single_pax = synth_pax_cnts.count(1)
        two_pax = synth_pax_cnts.count(2)
        three_pax = synth_pax_cnts.count(3)
        four_pax = synth_pax_cnts.count(4)
        self.assertTrue(set(synth_pax_cnts).issubset(range(1,5)))
        self.assertTrue(733 <= single_pax <= 753)
        self.assertTrue(165 <= two_pax <= 185)
        self.assertTrue(48 <= three_pax <= 68)
        self.assertTrue(14 <= four_pax <= 34)



    def load_bad_requests_missing_col(self):
        self.assertRaises(ValueError, load_requests, self.MISSING_COL_REQUESTS_FILE)


    def load_bad_requests_unexpected_dtype(self):
        self.assertRaises(AssertionError, load_requests, self.UNEXPECTED_DTYPE_REQUESTS_FILE)


    def test_filter_nulls(self):
        no_null_reqs_df = load_requests(self.GOOD_TEST_REQUESTS_FILE)
        self.assertEqual(len(filter_nulls(no_null_reqs_df)), 20)

        null_reqs_df = pd.read_csv(self.CONTAINS_NULLS_REQUESTS_FILE)
        null_reqs_df['passengers'] = 1 #null in test data
        self.assertEqual(len(filter_nulls(null_reqs_df)), 20)


    def test_filter_short_trips(self):
        nyc_reqs_df = pd.read_csv(self.TEST_NYC_REQUESTS_FILE)
        self.assertEqual(len(filter_short_distance_trips(nyc_reqs_df, min_miles=0.05)), 1497)


    def test_filter_requests_outside_oper_area(self):
        nyc_reqs_df = pd.read_csv(self.TEST_NYC_REQUESTS_FILE)
        self.assertEqual(len(filter_requests_outside_oper_area(nyc_reqs_df, self.MANHATTAN_OPERATING_AREA)), 1328)
        self.assertRaises(AssertionError, filter_requests_outside_oper_area, nyc_reqs_df, self.AUSTIN_OPERATING_AREA)


    def test_calculate_road_vmt_scaling_factor(self):
        reqs_df = pd.read_csv(self.GOOD_TEST_REQUESTS_FILE)
        self.assertAlmostEqual(calculate_road_vmt_scaling_factor(reqs_df), 1.336, places=3)


    def test_calculate_average_driving_speed(self):
        reqs_df = load_requests(self.GOOD_TEST_REQUESTS_FILE)
        self.assertAlmostEqual(calculate_average_driving_speed(reqs_df), 29.3, places=1)


if __name__ == '__main__':
    unittest.main()
