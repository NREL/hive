"""
Functions for pooling trips with Mean-Shift Clustering
author: tgrushka
"""

import pandas as pd
import numpy as np
from numpy import mean, absolute
from sklearn.cluster import MeanShift
#from sklearn.preprocessing import StandardScaler
#from sklearn.externals.joblib._parallel_backends import AutoBatchingMixin
from sklearn.externals.joblib import parallel

parallel.MIN_IDEAL_BATCH_DURATION = 1.
parallel.MAX_IDEAL_BATCH_DURATION = parallel.MIN_IDEAL_BATCH_DURATION * 10

import multiprocessing
import utm
import logging
import warnings
from math import sqrt
from datetime import datetime
import pdb

# pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.max_columns', 10)

class ZoneError(Exception):
    """Raised when coordinates fall in different UTM zones."""
    pass


def pool_locations(trips_df, distance_window_meters, col_names=['dropoff_latitude', 'dropoff_longitude'], strict=False, require_same_utm_zone=True, bandwidth_reduction=0.9, max_cores=0):
    print("====================")
    print("POOLING {} locations:".format(len(trips_df)))
    print("Distance Window = {} m ({} ft), Strict = {}".format(distance_window_meters, round(distance_window_meters * 3.28084), strict))
    print("====================")
    print("Started at: " + str(datetime.now()))
    
    # Not very DRY: Copied transform code from pool_trips;
    # Should refactor:
    
    # Transform coordinates to UTM (unit = meters)
    # col_names[0] = name of 'pickup_latitude' column ... etc.
    print("Transforming location coordinates to UTM...")
    location = pd.DataFrame(trips_df[[col_names[0], col_names[1]]].apply(lambda x: utm.from_latlon(x[0], x[1]), axis=1).tolist())
    location.set_index(trips_df.index, inplace=True)
    location.columns = ['easting', 'northing', 'zone', 'letter']
    
    """
    We need to check that all coordinates are in the same UTM zone.
    Otherwise, the pooling results will be incorrect.
    Handle edge cases later. For now, ignore the zone and just
    check all are in same zone, and raise exception / warning if not.
    """
    
    same_utm = (len(location.zone.unique()) == 1 and
                len(location.letter.unique()) == 1)
    
    if not same_utm:
        message = "Locations fall in multiple UTM zones! This will result in incorrect pooling results."
        if require_same_utm_zone:
            raise ZoneError(message)
        else:
            warnings.warn(message)
    
    zone = location.zone.iloc[0]
    letter = location.letter.iloc[0]
    print("UTM zone: {} {}".format(zone, letter))
    
    print("Building MeanShift DataFrame...")
    meanshift_df = pd.DataFrame({
        'location_easting': location.easting,
        'location_northing': location.northing
    })
    
    bandwidth = int(distance_window_meters)
    
    n_cores = max_cores
    n_cores = 0
    if n_cores == 0:
        n_cores = multiprocessing.cpu_count()
    
    n_jobs = int((1 + n_cores) / 2)
    # NEED TO CHANGE THIS WHEN WE GET PARALLEL WORKING!!
    #n_jobs = 1
    n_jobs=48
    
    # YES THIS IS ALMOST A DUPLICATE OF BELOW BUT DIFFERENT -- NOT VERY DRY:
    def _meanshift_algo(unpooled_df, iteration=0, starting_label=0):
        this_start_time = datetime.now()
        if iteration == 0:
            start_time = datetime.now()
        
        # reduce bandwidth for each iteration
        adjusted_bandwidth = int(bandwidth * bandwidth_reduction ** iteration)
        print("MeanShift iteration " + str(iteration + 1) + ": " + str(len(unpooled_df)) + " trips, bandwidth = " + str(adjusted_bandwidth) + " ...")
        
        # setup MeanShift and fit data:
        ms = MeanShift(bandwidth=adjusted_bandwidth, n_jobs=n_jobs)
        ms.fit(unpooled_df[['location_easting', 'location_northing']])
        
        # # of clusters = # of unique labels
        n_clusters = len(np.unique(ms.labels_))
        print("Found " + str(n_clusters) + " clusters of " + str(len(unpooled_df)) + " remaining unpooled trips...")
        
        # ensure new labels are unique:
        labels = ms.labels_ + starting_label
        
        # assign cluster centers to a DataFrame:
        clusters = pd.DataFrame(ms.cluster_centers_).astype(np.int64)
        clusters.columns = ['location_easting', 'location_northing']
        
        # the clusters should be associated with the unique labels in ascending order:
        clusters.set_index(np.unique(labels), inplace=True)
        
        # assign the labels to the unpooled df
        unpooled_df.set_index(labels, inplace=True)
        
        clusters = clusters.assign(trips = unpooled_df.groupby(unpooled_df.index).location_easting.count())
        
        if not strict:
            print("strict==False :. skipping further iterations.")
        if strict: # iterate only if strict=True
            # collect labels that exceed the window
            #exceeding_df = pd.DataFrame(columns=['label', 'count', 'max'])
            exceeding_labels = []
            for i in clusters[clusters.trips > 1].index:
                x = unpooled_df[labels == i]
                northing_range = max(x.location_northing) - min(x.location_northing)
                easting_range = max(x.location_easting) - min(x.location_easting)
                distance_range = sqrt(northing_range ** 2 + easting_range ** 2)
                if distance_range > bandwidth:
                    exceeding_labels += [i]
            
            # the labels exceeding the window are the index of the df we just created
            #exceeding_labels = np.array(exceeding_df.index)
            print(str(len(exceeding_labels)) + " of these clusters exceeded window limits.")
            print("-------------------- " + str(datetime.now() - this_start_time))
            
            # check if we need to recurse:
            if len(exceeding_labels) > 0:
                # drop 'invalid' clusters that are being repooled anyway:
                clusters.drop(exceeding_labels, inplace=True)
                
                # calculate safe next starting label value:
                next_label = starting_label + n_clusters
                #print("next_label = " + str(next_label))
                
                # get a logical index of trips in pools exceeding the window:
                exceeding_indices = np.isin(labels, exceeding_labels)
                
                # run the algorithm recursively:
                new_labels, new_clusters = _meanshift_algo(unpooled_df[exceeding_indices], iteration=(iteration + 1), starting_label=next_label)
                
                # relabel the repooled trips:
                #print("Relabeling...")
                unpooled_df = unpooled_df.assign(label = unpooled_df.index)
                unpooled_df.loc[exceeding_indices, 'label'] = new_labels
                unpooled_df.set_index(unpooled_df.label, inplace=True)
                unpooled_df.drop('label', axis=1, inplace=True)
                
                # append the new clusters:
                clusters = clusters.append(new_clusters, sort=False)
                
        if iteration == 0:
            total_pools = str(len(np.unique(unpooled_df.index)))
            pooling_ratio = float(total_pools) / float(len(meanshift_df))
            
            print("==================== " + str(datetime.now() - start_time))
            
            print("TOTAL POOLS: " + str(total_pools))
            print("POOL STATS: (# locations in pool, # pools)")
            for i in np.unique(clusters.trips):
                print("{}\t{}".format(i, len(clusters[clusters.trips == i])))
            print("POOLING RATIO: " + str(round(pooling_ratio, 3)))
        return (unpooled_df.index, clusters)
    
    print("===== Starting MeanShift, jobs = {}, bandwidth reduction = {} =====".format(n_jobs, bandwidth_reduction))
    labels, clusters = _meanshift_algo(meanshift_df)
    
    cluster_location = pd.DataFrame(clusters[['location_easting', 'location_northing']].apply(lambda x: utm.to_latlon(x['location_easting'], x['location_northing'], zone, letter), axis=1).tolist())
    cluster_location.set_index(clusters.index, inplace=True)
    cluster_location.columns = ['location_latitude', 'location_longitude']
    
    clusters = clusters.join(cluster_location)
    clusters = clusters[['trips', 'location_latitude', 'location_longitude']]
    
    print("Finished at: " + str(datetime.now()))
    
    return (labels, clusters)


def pool_trips(trips_df, time_window_seconds, distance_window_meters, col_names=['pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude', 'pickup_datetime', 'passenger_count'], require_same_utm_zone=True, bandwidth_reduction=0.9, max_cores=0):
    """
    col_names = ordered names of appropriate columns in input DataFrame:
        ['pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude', 'pickup_datetime', 'passenger_count']
    bandwidth_reduction = multiplier to reduce bandwidth each iteration [default = 0.9]
    """
    print("====================")
    print("POOLING {} TRIPS:".format(len(trips_df)))
    print("Time Window = {} s ({} min)".format(time_window_seconds, round(time_window_seconds / 60.0, 1)))
    print("Distance Window = {} m ({} ft)".format(distance_window_meters, round(distance_window_meters * 3.28084)))
    print("====================")
    print("Started at: " + str(datetime.now()))
    time_multiplier = float(distance_window_meters) / float(time_window_seconds)
    
    print("Converting time to epoch (seconds since 1970)...")
    pickup_epoch = pd.to_datetime(trips_df[col_names[4]]).astype(np.int64) // 1e9
    
    print("Scaling time epoch by {} such that {} seconds ≍ {} meters".format(round(time_multiplier, 4), time_window_seconds, distance_window_meters))
    scaled_time = pickup_epoch * time_multiplier
    
    # Transform coordinates to UTM (unit = meters)
    # col_names[0] = name of 'pickup_latitude' column ... etc.
    print("Transforming pickup coordinates to UTM...")
    pickup = pd.DataFrame(trips_df[[col_names[0], col_names[1]]].apply(lambda x: utm.from_latlon(x[0], x[1]), axis=1).tolist())
    pickup.set_index(trips_df.index, inplace=True)
    pickup.columns = ['easting', 'northing', 'zone', 'letter']
    print("Transforming dropoff coordinates to UTM...")
    dropoff = pd.DataFrame(trips_df[[col_names[2], col_names[3]]].apply(lambda x: utm.from_latlon(x[0], x[1]), axis=1).tolist())
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
        message = "Trip start/endpoints are in multiple UTM zones! This will result in incorrect pooling results."
        if require_same_utm_zone:
            raise ZoneError(message)
        else:
            warnings.warn(message)
    
    #pdb.set_trace()
    
    zone = pickup.zone.iloc[0]
    letter = pickup.letter.iloc[0]
    print("UTM zone: {} {}".format(zone, letter))
    
    print("Building MeanShift DataFrame...")
    meanshift_df = pd.DataFrame({
        'scaled_time': scaled_time,
        'pickup_easting': pickup.easting,
        'pickup_northing': pickup.northing,
        'dropoff_easting': dropoff.easting,
        'dropoff_northing': dropoff.northing,
        'passengers': trips_df[col_names[5]]
    })
    
    # meanshift_df
    
    bandwidth = int(distance_window_meters)
    
    n_cores = max_cores
    if n_cores == 0:
        n_cores = multiprocessing.cpu_count()
    
    # DELETE -- TESTING ONLY!
    #n_cores = 1
    #bandwidth=600
    #iteration=0
    #bandwidth_reduction = 0.9
    
    # n_jobs = int((1 + n_cores) / 2)
    # NEED TO CHANGE THIS WHEN WE GET PARALLEL WORKING!!
    n_jobs = 1
    
    def _meanshift_algo(unpooled_df, iteration=0, starting_label=0):
        this_start_time = datetime.now()
        if iteration == 0:
            start_time = datetime.now()
        
        # reduce bandwidth for each iteration
        adjusted_bandwidth = int(bandwidth * bandwidth_reduction ** iteration)
        print("MeanShift iteration " + str(iteration + 1) + ": " + str(len(unpooled_df)) + " trips, bandwidth = " + str(adjusted_bandwidth) + " ...")
        
        # setup MeanShift and fit data:
        ms = MeanShift(bandwidth=adjusted_bandwidth, n_jobs=n_jobs)
        ms.fit(unpooled_df[['scaled_time', 'pickup_easting', 'pickup_northing', 'dropoff_easting', 'dropoff_northing']])
        
        # # of clusters = # of unique labels
        n_clusters = len(np.unique(ms.labels_))
        print("Found " + str(n_clusters) + " clusters of " + str(len(unpooled_df)) + " remaining unpooled trips...")
        
        # ensure new labels are unique:
        labels = ms.labels_ + starting_label
        
        # assign cluster centers to a DataFrame:
        clusters = pd.DataFrame(ms.cluster_centers_).astype(np.int64)
        clusters.columns = ['scaled_time', 'pickup_easting', 'pickup_northing', 'dropoff_easting', 'dropoff_northing']
        
        # the clusters should be associated with the unique labels in ascending order:
        clusters.set_index(np.unique(labels), inplace=True)
        
        # assign the labels to the unpooled df
        unpooled_df.set_index(labels, inplace=True)
        
        clusters = clusters.assign(trips = unpooled_df.groupby(unpooled_df.index).scaled_time.count())
        
        # collect labels that exceed the window
        #exceeding_df = pd.DataFrame(columns=['label', 'count', 'max'])
        exceeding_labels = []
        for i in clusters[clusters.trips > 1].index:
            x = unpooled_df[labels == i]
            northing_range = max(x.pickup_northing) - min(x.pickup_northing)
            easting_range = max(x.pickup_easting) - min(x.pickup_easting)
            pickup_distance_range = sqrt(northing_range ** 2 + easting_range ** 2)
            northing_range = max(x.dropoff_northing) - min(x.dropoff_northing)
            easting_range = max(x.dropoff_easting) - min(x.dropoff_easting)
            dropoff_distance_range = sqrt(northing_range ** 2 + easting_range ** 2)
            time_range = max(x.scaled_time) - min(x.scaled_time)
            max_value = max(time_range, pickup_distance_range, dropoff_distance_range)
            if max_value > bandwidth:
                #exceeding_df = exceeding_df.append(pd.DataFrame({ 'count': len(x), 'max': int(round(max_value)) }, index=[i]), sort=False)
                exceeding_labels += [i]
        
        # the labels exceeding the window are the index of the df we just created
        #exceeding_labels = np.array(exceeding_df.index)
        print(str(len(exceeding_labels)) + " of these clusters exceeded window limits.")
        print("-------------------- " + str(datetime.now() - this_start_time))
        
        # check if we need to recurse:
        if len(exceeding_labels) > 0:
            # drop 'invalid' clusters that are being repooled anyway:
            clusters.drop(exceeding_labels, inplace=True)
            
            # calculate safe next starting label value:
            next_label = starting_label + n_clusters
            #print("next_label = " + str(next_label))
            
            # get a logical index of trips in pools exceeding the window:
            exceeding_indices = np.isin(labels, exceeding_labels)
            
            # run the algorithm recursively:
            new_labels, new_clusters = _meanshift_algo(unpooled_df[exceeding_indices], iteration=(iteration + 1), starting_label=next_label)
            
            # relabel the repooled trips:
            #print("Relabeling...")
            unpooled_df = unpooled_df.assign(label = unpooled_df.index)
            unpooled_df.loc[exceeding_indices, 'label'] = new_labels
            unpooled_df.set_index(unpooled_df.label, inplace=True)
            unpooled_df.drop('label', axis=1, inplace=True)
            
            # append the new clusters:
            clusters = clusters.append(new_clusters, sort=False)
        if iteration == 0:
            total_pools = str(len(np.unique(unpooled_df.index)))
            pooling_ratio = float(total_pools) / float(len(meanshift_df))
            
            print("==================== " + str(datetime.now() - start_time))
            
            print("Counting passengers and trips per cluster...")
            
            clusters = clusters.assign(
                trips = unpooled_df.groupby(unpooled_df.index).passengers.count(),
                passengers = unpooled_df.groupby(unpooled_df.index).passengers.sum()
            )
            
            
            print("TOTAL POOLS: " + str(total_pools))
            print("POOL STATS: (# trips in pool, # pools, total pax)")
            for i in np.unique(clusters.trips):
                print("{}\t{}\t{}".format(i, len(clusters[clusters.trips == i]), sum(clusters[clusters.trips == i].passengers)))
            print("POOLING RATIO: " + str(round(pooling_ratio, 3)))
        return (unpooled_df.index, clusters)
    
    print("===== Starting MeanShift, jobs = {}, bandwidth reduction = {} =====".format(n_jobs, bandwidth_reduction))
    labels, clusters = _meanshift_algo(meanshift_df)
    
    clusters = clusters.assign(pickup_epoch = (clusters.scaled_time / time_multiplier).astype(np.int64))
    clusters = clusters.assign(pickup_datetime = clusters.pickup_epoch.apply(datetime.utcfromtimestamp))
    cluster_pickup = pd.DataFrame(clusters[['pickup_easting', 'pickup_northing']].apply(lambda x: utm.to_latlon(x['pickup_easting'], x['pickup_northing'], zone, letter), axis=1).tolist())
    cluster_dropoff = pd.DataFrame(clusters[['dropoff_easting', 'dropoff_northing']].apply(lambda x: utm.to_latlon(x['dropoff_easting'], x['dropoff_northing'], zone, letter), axis=1).tolist())
    cluster_pickup.set_index(clusters.index, inplace=True)
    cluster_pickup.columns = ['pickup_latitude', 'pickup_longitude']
    cluster_dropoff.set_index(clusters.index, inplace=True)
    cluster_dropoff.columns = ['dropoff_latitude', 'dropoff_longitude']

    clusters = clusters.join(cluster_pickup).join(cluster_dropoff)
    clusters = clusters[['trips', 'pickup_datetime', 'pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude']]
    
    print("Finished at: " + str(datetime.now()))
    
    return (labels, clusters)
