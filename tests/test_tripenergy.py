import unittest
import sys
import os

from hive.tripenergy import import_whmi_template, create_scaled_whmi, \
    calc_trip_kwh, calc_idle_kwh

TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')

class TripEnergyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.WHMI_LOOKUP_FILE = os.path.join(TEST_INPUT_DIR, '.lib', 'wh_mi_lookup.csv')

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_whmi_template(self):
        whmi_template = import_whmi_template(self.WHMI_LOOKUP_FILE)
        self.assertTrue(whmi_template is not None)

    def test_create_scaled_whmi(self):
        whmi_template = import_whmi_template(self.WHMI_LOOKUP_FILE)
        scaled_whmi_lookup = create_scaled_whmi(whmi_template, 0.8)
        self.assertEqual(scaled_whmi_lookup['avg_spd_mph'][-1], 62.5)
        self.assertAlmostEqual(scaled_whmi_lookup['whmi'][0], 1.1487803568)

    def test_calc_trip_kwh(self):
        whmi_template = import_whmi_template(self.WHMI_LOOKUP_FILE)
        scaled_whmi_lookup = create_scaled_whmi(whmi_template, 0.8)
        self.assertAlmostEqual(calc_trip_kwh(10, 3600, scaled_whmi_lookup), 0.009620097104)

    def test_calc_idle_kwh(self):
        self.assertEqual(calc_idle_kwh(3600), 0.8)



if __name__ == '__main__':
    unittest.main()
