import unittest
import sys
import os

sys.path.append('../')
from hive.tripenergy import import_whmi_template, create_scaled_whmi, \
    calc_trip_kwh, calc_idle_kwh

import config as cfg

WHMI_LOOKUP_FILE = os.path.join(cfg.IN_PATH, '.lib', 'wh_mi_lookup.csv')

class TripEnergyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
    # this will run once before any of the test methods in this class

    # i.e. load or create sample dataset for the test class
        pass


    @classmethod
    def tearDownClass(cls):
    # this will run once after all of the test methods in this class

    # i.e. remove any files or databases that were created for testing
        pass

    def setUp(self):
    # This will run before EVERY test method in the class
        pass

    def tearDown(self):
    # This will run after EVERY test method in the class
        pass

    def test_import_whmi_template(self):
        whmi_template = import_whmi_template(WHMI_LOOKUP_FILE)
        self.assertTrue(whmi_template is not None)

    def test_create_scaled_whmi(self):
        whmi_template = import_whmi_template(WHMI_LOOKUP_FILE)
        scaled_whmi_lookup = create_scaled_whmi(whmi_template, 0.8)
        self.assertEqual(scaled_whmi_lookup['avg_spd_mph'][-1], 62.5)
        self.assertAlmostEqual(scaled_whmi_lookup['whmi'][0], 1.1487803568)

    def test_calc_trip_kwh(self):
        whmi_template = import_whmi_template(WHMI_LOOKUP_FILE)
        scaled_whmi_lookup = create_scaled_whmi(whmi_template, 0.8)
        self.assertAlmostEqual(calc_trip_kwh(10, 3600, scaled_whmi_lookup), 0.009620097104)

    def test_calc_idle_kwh(self):
        self.assertEqual(calc_idle_kwh(3600), 0.8)



if __name__ == '__main__':
    unittest.main()
