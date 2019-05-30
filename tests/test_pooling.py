"""
Tests for pooling module
author: tgrushka
"""

import sys
import random
import unittest
import pandas as pd
import numpy as np
import socket
import importlib
sys.path.append('../')
from hive import pooling
importlib.reload(pooling)

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
        
        if socket.gethostname() == "arnaud.hpc.nrel.gov":
            max_cores = 0
            file = "/data/mbap_shared/honda_data/raw_data/nyc_tlc/trip_data/trip_data_4.csv"
        elif socket.gethostname() == "tgrushka-32011s":
            max_cores = 1
            file = "~/Honda/nyc_20130411_18-21.csv"
        else:
            raise(ValueError, "I don't know where the CSV file is on this machine.")
        
        print("Loading {} ...".format(file))
        
        trips_df = pd.read_csv(file, \
            engine="c", \
            skipinitialspace=True, \
            usecols=['pickup_datetime', 'dropoff_datetime', 'passenger_count', 'pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude'], \
            dtype={ \
            'pickup_datetime': str, \
            'dropoff_datetime': str, \
            'passenger_count': int, \
            'pickup_latitude': np.float64, \
            'pickup_longitude': np.float64, \
            'dropoff_latitude': np.float64, \
            'dropoff_longitude': np.float64
        })
        
        # filter NYC by date:
        date_filter = "2013-04-11"
        print("Filtering trips on date {} ...".format(date_filter))
        trips_df = trips_df[trips_df.pickup_datetime.str.contains(date_filter)]
        
        print("Filtering out invalid trips...")
        # filter NYC for valid coordinates:
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
		
        print("Calling pooling.pool_trips ...")
        labels, clusters = pooling.pool_trips(trips_df, time_window_seconds=600, distance_window_meters=305, max_cores=max_cores)
        pass
        
if __name__ == '__main__':
    unittest.main()

