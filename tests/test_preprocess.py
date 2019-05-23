import sys
import random
import unittest

sys.path.append('../')
from hive.preprocess import gen_synth_pax_cnt, load_requests, \
filter_short_trips, filter_requests_outside_oper_area, \
calculate_road_vmt_scaling_factor, calculate_average_driving_speed

class PreProcessingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
    # this will run once before any of the test methods in this class
    # i.e. load or create sample dataset for the test class
    
    #TODO: add setup code for testing
        pass

    @classmethod
    def tearDownClass(cls):
    # this will run once after all of the test methods in this class
    # i.e. remove any files or databases that were created for testing

    #TODO: add setup code for testing
        pass

    def test_gen_synth_pax_cnt(self):
        random.seed(123)
        synth_pax_cnts = [gen_synth_pax_cnt() for i in range(1000)]
        single_pax = synth_pax_cnts.count(1)
        two_pax = synth_pax_cnts.count(2)
        three_pax = synth_pax_cnts.count(3)
        four_pax = synth_pax_cnts.count(4)
        self.assertTrue(synth_pax_cnts.issubset(range(1,5)))
        self.assertTrue(733 <= single_pax <= 753)
        self.assertTrue(165 <= two_pax <= 185)
        self.assertTrue(48 <= three_pax <= 68)
        self.assertTrue(14 <= four_pax <= 34)

    def test_load_requests(self):
        #TODO:
        pass

    def test_filter_short_trips(self):
        #TODO:
        pass

    def test_filter_requests_outside_oper_area(self):
        #TODO:
        pass

    def test_calculate_road_vmt_scaling_factor(self):
        #TODO:
        pass

    def test_calculate_average_driving_speed(self):
        #TODO:
        pass