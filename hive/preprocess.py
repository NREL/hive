"""
Functions that prepare raw data for simulation
"""

import sys
import os
import glob
import random
import numpy as np
import pandas as pd
import geopandas as gpd
from ast import literal_eval
from time import time
from datetime import datetime
from dateutil import parser
import logging
from haversine import haversine
from shapely.geometry import Point
from pandas.api.types import is_string_dtype
from pandas.api.types import is_numeric_dtype

from hive.constraints import ENV_PARAMS
from hive import units
from hive import utils

log = logging.getLogger('run_log')

def gen_synth_pax_cnt():
    """Randomly assigns passenger count from real-world distribution measured
    in 2016(?) in Denver, CO by Henao (NREL).
    """
    occ_distr = [1] * 743 + [2] * 175 + [3] * 58 + [4] * 24 #from Henao
    pax = random.choice(occ_distr)

    return pax


def load_requests(reqs_file, verbose=True, save_path=None):
        """Loads, combines, and sorts request csvs by pickup time
        into a Pandas DataFrame.
        """

        def name(path):
            return os.path.splitext(os.path.basename(path))[0]

        log.info("Loading requests file..")
        reqs_df = pd.read_csv(reqs_file)
        assert len(reqs_df) > 0, "No requests in file!"

        #check for existence of req fields
        #TODO: Make route optional
        req_fields = [
        'pickup_time',
        'dropoff_time',
        'distance_miles',
        'pickup_lat',
        'pickup_lon',
        'dropoff_lat',
        'dropoff_lon',
            # 'route_utm',
        ]

        for field in req_fields:
            if not field in reqs_df.columns:
                 raise ValueError("'{}' field required in requests input!".format(field))

        #check data types of req fields
        assert is_string_dtype(reqs_df['pickup_time']), """'pickup_time' in
        requests file not of str data type!"""
        assert is_string_dtype(reqs_df['dropoff_time']), """'dropoff_time' in
        requests file not of str data type!"""
        assert is_numeric_dtype(reqs_df['distance_miles']), """'distance_miles'
        in requests file not of numeric data type!"""
        assert is_numeric_dtype(reqs_df['pickup_lat']), """'pickup_lat'
        in requests file not of numeric data type!"""
        assert is_numeric_dtype(reqs_df['pickup_lon']), """'pickup_lon'
        in requests file not of numeric data type!"""
        assert is_numeric_dtype(reqs_df['dropoff_lat']), """'dropoff_lat'
        in requests file not of numeric data type!"""
        assert is_numeric_dtype(reqs_df['dropoff_lon']), """'dropoff_lon'
        in requests file not of numeric data type!"""

        #convert time strings to datetime objects
        # reqs_df['pickup_time'] = reqs_df['pickup_time'] \
        # .apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        # reqs_df['dropoff_time'] = reqs_df['dropoff_time'] \
        # .apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        # reqs_df.sort_values('pickup_time', inplace=True)

        log.info("  parsing datetime")
        reqs_df['pickup_time'] = reqs_df['pickup_time'].apply(lambda x: parser.parse(x))
        reqs_df['dropoff_time'] = reqs_df['dropoff_time'].apply(lambda x: parser.parse(x))

        #synthesize 'passengers' if not exists
        if 'passengers' not in reqs_df.columns: #apply real-world pax distr
            log.info("  synthesizing passenger counts")
            pax = [gen_synth_pax_cnt() for i in range(len(reqs_df))]
            reqs_df['passengers'] = pax

        if 'seconds' not in reqs_df.columns:
            log.info("  calculating trip times")
            reqs_df['seconds'] = reqs_df.apply(lambda row: (row.dropoff_time - row.pickup_time).total_seconds(), axis=1)

        #convert latitude and longitude to utm
        # if all(x not in reqs_df.columns for x in ['pickup_x', 'pickup_y', 'dropoff_x', 'dropoff_y']):
        #     log.info("    - converting coordinate system to utm")
        #     reqs_df['pickup_x'] = reqs_df.apply(lambda x: utm.from_latlon(x.pickup_lat, x.pickup_lon)[0], axis=1)
        #     reqs_df['pickup_y'] = reqs_df.apply(lambda x: utm.from_latlon(x.pickup_lat, x.pickup_lon)[1], axis=1)
        #     reqs_df['dropoff_x'] = reqs_df.apply(lambda x: utm.from_latlon(x.dropoff_lat, x.dropoff_lon)[0], axis=1)
        #     reqs_df['dropoff_y'] = reqs_df.apply(lambda x: utm.from_latlon(x.dropoff_lat, x.dropoff_lon)[1], axis=1)

        # reqs_df['route_utm'] = reqs_df.route_utm.apply(lambda x: eval(x))

        fields = req_fields + [
                                'passengers',
                                'seconds',
                                # 'pickup_x',
                                # 'pickup_y',
                                # 'dropoff_x',
                                # 'dropoff_y',
                            ]

        #check data type of 'passengers' field
        assert is_numeric_dtype(reqs_df['passengers']), """'passengers'
        in requests file not of numeric data type!"""

        if save_path is not None:
            outfile = os.path.join(save_path, f'{name(reqs_file)}_HIVE_preprocessed.csv')
            reqs_df.to_csv(outfile)

        return reqs_df[fields]

def calculate_demand(reqs_df, timestep_s):
    gb = reqs_df.set_index('pickup_time').groupby(pd.Grouper(level='pickup_time', freq=f"{timestep_s}S"))
    demand = gb['dropoff_time'].count().reset_index(name='demand').demand.values

    return demand

def filter_nulls(reqs_df):
    """Filters requests that contain null values.
    """
    filt_reqs_df = reqs_df.dropna()
    filt_reqs_df.reset_index(inplace=True, drop=True)

    return filt_reqs_df

def filter_short_distance_trips(reqs_df, min_miles=0.05):
    """Filters requests that are less than min_miles (default=0.05). These
    extremely short distance trips are often measuring errors, i.e. not
    "actual" trips.
    """
    filt_reqs_df = reqs_df[reqs_df.distance_miles > min_miles].reset_index()
    filt_reqs_df.reset_index(inplace=True, drop=True)

    return filt_reqs_df

def filter_short_time_trips(reqs_df, min_time_s=1):
    """Filters requests that are less than min_time_s (default=1). These
    extremely short time trips are often measuring errors, i.e. not "acual"
    trips.
    """
    filt_reqs_df = reqs_df[(reqs_df['dropoff_time'] - reqs_df['pickup_time']).dt.total_seconds() >= min_time_s]
    filt_reqs_df.reset_index(inplace=True, drop=True)

    return filt_reqs_df

def filter_requests_outside_oper_area(reqs_df, geojson_file):
    """Filters requests in reqs_df whose origin or destination location are
    outside of the GeoJSON file.
    """
    op_area_gdf = gpd.read_file(geojson_file)
    pickup_pts, dropoff_pts = [], []
    for lon, lat in zip(reqs_df['pickup_lon'], reqs_df['pickup_lat']):
        pt = Point(lon, lat)
        pickup_pts.append(pt)
    for lon, lat in zip(reqs_df['dropoff_lon'], reqs_df['dropoff_lat']):
        pt = Point(lon, lat)
        dropoff_pts.append(pt)
    reqs_df['pickup_pts'] = pickup_pts
    reqs_df['dropoff_pts'] = dropoff_pts

    pickup_gdf = gpd.GeoDataFrame(reqs_df, geometry='pickup_pts')
    pickup_gdf.rename(columns={'pickup_pts': 'geometry'}, inplace=True)
    pickup_gdf.crs = op_area_gdf.crs #convert to matching crs
    filt_pickup_gdf = gpd.sjoin(pickup_gdf, op_area_gdf, how='inner', op='intersects')

    dropoff_gdf = gpd.GeoDataFrame(reqs_df, geometry='dropoff_pts')
    dropoff_gdf.rename(columns={'dropoff_pts': 'geometry'}, inplace=True)
    dropoff_gdf.crs = op_area_gdf.crs #convert to matching crs
    filt_dropoff_gdf = gpd.sjoin(dropoff_gdf, op_area_gdf, how='inner', op='intersects')

    comb_filt_gdf = filt_pickup_gdf.index.join(filt_dropoff_gdf.index, how='inner')
    filt_reqs_df = reqs_df.iloc[comb_filt_gdf]
    filt_reqs_df = filt_reqs_df.drop(columns=['pickup_pts', 'dropoff_pts'])
    filt_reqs_df = filt_reqs_df.reset_index(drop=True)

    assert len(filt_reqs_df) > 0, "No requests within operating area!"
    filt_reqs_df.reset_index(inplace=True, drop=True)

    return(filt_reqs_df)

def calculate_road_vmt_scaling_factor(reqs_df):
    """Estimates shortest path distance -> on-road scaling factor for estimating
    VMT between two points.
    """

    def row_haversine(row):
        pickup_loc = (row['pickup_lat'], row['pickup_lon'])
        dropoff_loc = (row['dropoff_lat'], row['dropoff_lon'])
        return haversine(pickup_loc, dropoff_loc, unit='mi')

    short_path_dists = reqs_df.apply(lambda row: row_haversine(row), axis=1)
    total_vmt = reqs_df['distance_miles'].sum()
    total_short_path_dist = short_path_dists.sum()
    haversine_scaling_factor = total_vmt/total_short_path_dist
    utils.assert_constraint('RN_SCALING_FACTOR', haversine_scaling_factor, ENV_PARAMS, context="Calculate Haversine Scaling Factor")

    return haversine_scaling_factor


def calculate_average_driving_speed(reqs_df):
    """Calculates average driving speed for all trips in dataset
    """

    def row_hours(row):
        timedelta_s = (row['dropoff_time'] - row['pickup_time']).total_seconds()
        return timedelta_s / 3600

    hrs = reqs_df.apply(lambda row: row_hours(row), axis=1)
    total_hrs = hrs.sum()
    total_vmt = reqs_df['distance_miles'].sum()
    avg_driving_mph = total_vmt/total_hrs
    utils.assert_constraint('DISPATCH_MPH', avg_driving_mph, ENV_PARAMS, context="Calculate Dispatch Speed")

    return avg_driving_mph
