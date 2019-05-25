"""
Tests for pooling module
author: tgrushka
"""

import sys
import random
import unittest
import pandas as pd

sys.path.append('../')
from hive.pooling import pool_trips

class PoolingTest(unittest.TestCase):
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
    
    def test_pool_trips(self):
        random.seed(123)
        trips_df = pd.read_csv("~/Honda/nyc_20130411_18-21.csv")
        trips_df = trips_df[trips_df.pickup_datetime.str.contains("2013-04-11 21")]
        trips_df = trips_df.loc[(
			(trips_df.pickup_latitude > 40) &
            (trips_df.pickup_latitude < 41) &
            (trips_df.pickup_longitude > -75) &
            (trips_df.pickup_longitude < -73) &
            (trips_df.dropoff_latitude > 40) &
            (trips_df.dropoff_latitude < 41) &
            (trips_df.dropoff_longitude > -75) &
            (trips_df.dropoff_longitude < -73)
        )]
		
        pool_trips(trips_df, 600, 305)
        pass
        
if __name__ == '__main__':
    unittest.main()
