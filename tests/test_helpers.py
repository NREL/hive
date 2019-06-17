import os
import sys
import unittest

sys.path.append('../')
from hive.helpers import estimate_vmt

DEFAULT_INPUT_DIR = os.path.join('..', 'inputs', '.inputs_default')
TEST_INPUT_DIR = '.tmp'

class HelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.OLAT = 40.7082956
        cls.OLON = -74.0120053
        cls.DLAT = 40.7651258
        cls.DLON = -73.9799236
        cls.VMT_SCALING_FACTOR = 1.38

    def test_estimate_vmt(self):
        vmt = estimate_vmt(self.OLAT, 
                        self.OLON,
                        self.DLAT,
                        self.DLON,
                        self.VMT_SCALING_FACTOR)
        self.assertTrue(4.5 <= vmt <= 7.5)

if __name__ == '__main__':
    unittest.main()

