import unittest
import pandas as pd
import sys
import matplotlib.pyplot as plt

sys.path.append('../')
from hive import charging

class ChargingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PATH_TO_LEAF = '../inputs/.lib/raw_leaf_curves.csv'
        cls.leaf_df = pd.read_csv(PATH_TO_LEAF)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_construct_charge_profile(self):
        battery_kwh = 30
        battery_kw = 100
        charge_time = 3600
        soc_i = 20
        soc_f = 80
        
        scaled_df = charging.construct_temporal_charge_template(self.leaf_df,
                                                                battery_kwh, 
                                                                battery_kw)

        charge_df = charging.construct_charge_profile(scaled_df, 
                                                        soc_i = soc_i, 
                                                        soc_f = soc_f)

        # TODO: add some assertion to test scaled_df and charge_df

    def test_calc_const_charge_kwh(self):

        kwh_out = charging.calc_const_charge_kwh(1800, kw=6.6)

        self.assertEqual(kwh_out, 3.3)    


    def test_calc_const_charge_secs(self):

        secs_out = charging.calc_const_charge_secs(init_energy_kwh = 8, 
                                                 battery_capacity_kwh = 40, 
                                                 kw=6.6, 
                                                 soc_f=1.0)
        
        self.assertEqual(secs_out, 17454.545454545456)   

    def test_calc_dcfc_kwh(self):
        print(charging.calc_dcfc_kwh(30, 50, 20, 600))

    def test_calc_dcfc_secs(self):
        print(charging.calc_dcfc_secs(30, 50, 20, 80))