"""
Functions for pooling trips with Mean-Shift Clustering
author: tgrushka
"""

import pandas as pd
import numpy as np
from numpy import mean, absolute
from sklearn.cluster import MeanShift
from sklearn.preprocessing import StandardScaler
from sklearn.externals.joblib._parallel_backends import AutoBatchingMixin
import multiprocessing
import utm
import logging
import warnings

# pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.max_columns', 10)

class ZoneError(Exception):
    """Raised when coordinates fall in different UTM zones."""
    pass

def pool_trips(trips_df, time_window_seconds, distance_window_meters, require_same_utm_zone=True, max_cores=0):
    """
    distance_window_meters = # of meters in X and Y directions (considered separately)
    """
    time_multiplier = float(distance_window_meters) / float(time_window_seconds)
    
    print("Converting time to epoch (seconds since 1970)...")
    pickup_epoch = pd.to_datetime(trips_df.pickup_datetime).astype(np.int64) // 1e9
    
    print("Multiplying time (seconds) by {}".format(time_multiplier))
    scaled_time = pickup_epoch * time_multiplier
    
    # Transform coordinates to UTM (unit = meters)
    print("Transforming pickup coordinates to UTM (unit = meters)...")
    pickup = pd.DataFrame(trips_df[['pickup_latitude', 'pickup_longitude']].apply(lambda x: utm.from_latlon(x[0], x[1]), axis=1).tolist())
    pickup.set_index(trips_df.index, inplace=True)
    pickup.columns = ['easting', 'northing', 'zone', 'letter']
    print("Transforming dropoff coordinates to UTM (unit = meters)...")
    dropoff = pd.DataFrame(trips_df[['dropoff_latitude', 'dropoff_longitude']].apply(lambda x: utm.from_latlon(x[0], x[1]), axis=1).tolist())
    dropoff.set_index(trips_df.index, inplace=True)
    dropoff.columns = ['easting', 'northing', 'zone', 'letter']
    
    """
    We need to check that all coordinates are in the same UTM zone.
    Otherwise, the pooling results will be incorrect.
    Handle edge cases later. For now, ignore the zone and just
    check all are in same zone, and raise exception / warning if not.
    """
    
    same_utm = (len(pickup.zone.unique()) == 1 and
                len(pickup.letter.unique()) == 1 and
                len(dropoff.zone.unique()) == 1 and
                len(dropoff.letter.unique()) == 1 and
                all(pickup.zone == dropoff.zone) and
                all(pickup.letter == dropoff.letter))
    
    if not same_utm:
        message = "Locations fall in different UTM zones! This may impact pooling results."
        if require_same_utm_zone:
            raise ZoneError(message)
        else:
            warnings.warn(message)
    
    print("Merging data...")
    meanshift_df = pd.DataFrame({
        'scaled_time': scaled_time.round().astype(np.int64),
        'pickup_easting': pickup.easting.round().astype(np.int64),
        'pickup_northing': pickup.northing.round().astype(np.int64),
        'dropoff_easting': dropoff.easting.round().astype(np.int64),
        'dropoff_northing': dropoff.northing.round().astype(np.int64)
    })
    
    # print(meanshift_df)
    
    bandwidth = int(distance_window_meters)
    print("MeanShift bandwidth = {}".format(bandwidth))
    
    n_cores = max_cores
    if n_cores == 0:
        n_cores = multiprocessing.cpu_count()
    n_cores = 1
    
    ms = MeanShift(bandwidth=bandwidth, n_jobs=n_cores)
    ms.fit(meanshift_df)
    
    labels = ms.labels_
    cluster_centers = ms.cluster_centers_
    labels_unique = np.unique(labels)
    n_clusters = len(labels_unique)
    
    print("Grouped " + str(len(trips_df)) + " trips into " + str(n_clusters) + " clusters.")
    print("POOLING RATIO = " + str(round(float(n_clusters) / len(trips_df), 4)))
    
    
    pass
