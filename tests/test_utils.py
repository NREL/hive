import unittest
import os
import shutil
import pandas as pd
import pickle

from hive import utils

TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join('tests', '.tmp')

class UtilsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)
        df1 = pd.DataFrame({'a': [1], 'b': [2], 'c': [3]})
        df2 = pd.DataFrame({'d': [4], 'e': [5], 'f': [6]})
        cls.test_data = {'df1': df1, 'df2': df2}
        cls.log_columns = ['a', 'b', 'c']
        cls.CONSTRAINTS = {
                            'BETWEEN': ('between', 0, 2),
                            'BETWEEN_INCL': ('between_incl', 0, 2),
                            'GREATER_THAN': ('greater_than', 0),
                            'LESS_THAN': ('less_than', 2),
                            'IN_SET': ('in_set', ['A', 'B']),
                            }

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_save_to_hdf(self):
        outfile = os.path.join(TEST_OUTPUT_DIR, 'test_file.h5')
        utils.save_to_hdf(self.test_data, outfile)

        data1 = pd.read_hdf(outfile, key='df1')
        data2 = pd.read_hdf(outfile, key='df2')

        self.assertEqual(data1.a.iloc[0], 1)
        self.assertEqual(data2.f.iloc[0], 6)

    def test_save_to_pickle(self):
        outfile = os.path.join(TEST_OUTPUT_DIR, 'test_file.pickle')
        utils.save_to_pickle(self.test_data, outfile)

        with open(outfile, 'rb') as f:
            data = pickle.load(f)

        self.assertEqual(data['df1'].a.iloc[0], 1)
        self.assertEqual(data['df2'].f.iloc[0], 6)

    def test_initialize_log(self):
        outfile = os.path.join(TEST_OUTPUT_DIR, 'test_init_log.csv')
        utils.initialize_log(self.log_columns, outfile)

        df = pd.read_csv(outfile)
        jg
        self.assertEqual(list(df.columns.values), self.log_columns)

    def test_write_log(self):
        outfile = os.path.join(TEST_OUTPUT_DIR, 'test_write_log.csv')
        utils.initialize_log(self.log_columns, outfile)
        data = [1,2,3]
        utils.write_log(data, outfile)

        df = pd.read_csv(outfile)

        self.assertEqual(df.a.iloc[0], 1)

    def test_build_output_dir(self):
        utils.build_output_dir('test_scenario', TEST_OUTPUT_DIR)
        scenario_path = os.path.join(TEST_OUTPUT_DIR, 'test_scenario')
        log_path = os.path.join(scenario_path, 'logs')
        summaries_path = os.path.join(scenario_path, 'summaries')

        self.assertTrue(os.path.isdir(scenario_path))
        self.assertTrue(os.path.isdir(log_path))
        self.assertTrue(os.path.isdir(summaries_path))

    def test_assert_constraint_between(self):
        with self.assertRaises(Exception) as context:
            utils.assert_constraint('BETWEEN', 0, self.CONSTRAINTS)

        expected_error = "Param BETWEEN:0 is under low limit 0"

        self.assertTrue(expected_error in str(context.exception))

    def test_assert_constraint_between_incl(self):
        with self.assertRaises(Exception) as context:
            utils.assert_constraint('BETWEEN_INCL', -1, self.CONSTRAINTS)

        expected_error = "Param BETWEEN_INCL:-1 is under low limit 0"

        self.assertTrue(expected_error in str(context.exception))

    def test_assert_constraint_greater_than(self):
        with self.assertRaises(Exception) as context:
            utils.assert_constraint('GREATER_THAN', -1, self.CONSTRAINTS)

        expected_error = "Param GREATER_THAN:-1 is under low limit 0"

        self.assertTrue(expected_error in str(context.exception))

    def test_assert_constraint_less_than(self):
        with self.assertRaises(Exception) as context:
            utils.assert_constraint('LESS_THAN', 3, self.CONSTRAINTS)

        expected_error = "Param LESS_THAN:3 is over high limit 2"

        self.assertTrue(expected_error in str(context.exception))

    def test_assert_constraint_in_set(self):
        with self.assertRaises(Exception) as context:
            utils.assert_constraint('IN_SET', 'C', self.CONSTRAINTS)

        expected_error = "Param IN_SET:C must be from set"

        self.assertTrue(expected_error in str(context.exception))
