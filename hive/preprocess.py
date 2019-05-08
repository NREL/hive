"""
Functions that prepare raw data for simulation
"""

import sys
import glob
import random 
import numpy as np
import pandas as pd
import geopandas as gpd
from time import mktime
from datetime import datetime
from haversine import haversine
from shapely.geometry import Point
from pandas.api.types import is_string_dtype
from pandas.api.types import is_numeric_dtype
sys.path.append('../')
import inputs as inpt


def gen_synth_pax_cnt():
    """Randomly assigns passenger count from real-world distribution measured
    in 2016(?) in Denver, CO by Henao (NREL).
    """
    occ_distr = [1] * 743 + [2] * 175 + [3] * 58 + [4] * 24 #from Henao
    pax = random.choice(occ_distr)
    
    return pax

def load_requests(reqs_path):
        """Loads, combines, and sorts request csvs by pickup time 
        into a Pandas DataFrame.
        """
        req_files = glob.glob(reqs_path+'/*.csv')
        df_from_each_file = [pd.read_csv(f) for f in req_files]
        assert (len(df_from_each_file) > 0), "No CSVs in {}!".format(reqs_path)
        if len(df_from_each_file) == 1:
            reqs_df = df_from_each_file[0]
        else:
            reqs_df = pd.concat(df_from_each_file, ignore_index=True)

        #check for existence of req fields
        req_fields = [
        'pickup_time',
        'dropoff_time', 
        'distance_miles', 
        'pickup_lat', 
        'pickup_lon',
        'dropoff_lat', 
        'dropoff_lon']

        for field in req_fields:
            if not field in reqs_df.columns:
                 raise ValueError("'{}' field required in requests input!".format(field))

        reqs_df['pickup_time'] = reqs_df['pickup_time'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        reqs_df['dropoff_time'] = reqs_df['dropoff_time'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        reqs_df.sort_values('pickup_time', inplace=True)

        if 'passengers' not in reqs_df.columns: #apply real-world pax distr
            pax = [gen_synth_pax_cnt() for i in range(len(reqs_df))]
            reqs_df['passengers'] = pax
        
        return reqs_df

def filter_short_trips(reqs_df, min_miles=0.05):
    """Filters requests that are less than min_miles (default=0.05). These
    extremely short distance trips are often measuring errors, i.e. not 
    "actual" trips.
    """
    filt_reqs_df = reqs_df[reqs_df.distance_miles > min_miles]
    filt_reqs_df = filt_reqs_df.reset_index()

    return(filt_reqs_df)

def filter_requests_outside_oper_area(reqs_df, shp_file):
    """Filters requests in reqs_df whose origin or destination location are 
    outside of the shapefile found in op_area_path.
    """
    op_area_gdf = gpd.read_file(shp_file)
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
    filt_reqs_df = filt_reqs_df.reset_index()
    
    return(filt_reqs_df)

# def timestamp_to_unix(ts, tz):
#     """Converts Pandas timestamp object, ts with timezone, tz to unix time. tz
#     should be a pytz string, e.g. - ('US/Alaska', 'US/Arizona', 'US/Central',
#     'US/East-Indiana', 'US/Eastern', 'US/Hawaii', 'US/Indiana-Starke', 
#     'US/Michigan', 'US/Mountain', 'US/Pacific', 'US/Pacific-New', etc.) 
#     """
#     utc_ts = ts.tz_localize(tz)
#     unix_ts = mktime(ts.timetuple())
    
#     return unix_ts


# def scaled_haversine_dists(olats, olons, dlats, dlons, scaling_factor=inpt.RN_SCALING_FACTOR, units='mi'):
#     scaled_hav_dists = []
#     for olat, olon, dlat, dlon in zip(olats, olons, dlats, dlons):
#         dist = haversine((olat, olon), (dlat, dlon), unit=units) * scaling_factor
#         scaled_hav_dists.append(dist)
        
#     return scaled_hav_dists

# def generate_synth_pax_counts(request_cnt):
#     occ_distr = [1] * 743 + [2] * 175 + [3] * 58 + [4] * 24 #from Henao
#     random.shuffle(occ_distr)
#     pax = np.array(occ_distr)[:request_cnt].sum()
#     return pax

# def split_trips(df, passengers):
#     """When 'passenger_count' > vehicle capacity, the
#     trip request is split into multiple requests s.t. all
#     requests have a 'passenger_count' <= vehicle capacity."""

#     while df.passenger_count.max() > passengers:
#         single_trip_df = df[df.passenger_count<=passengers]
#         multi_trip_df = df[df.passenger_count>passengers]
#         pass_lst = list(multi_trip_df['passenger_count'] - passengers)
#         pass_lst.extend([passengers]*len(multi_trip_df))
#         multi_trip_df = multi_trip_df.append(multi_trip_df)
#         multi_trip_df['passenger_count'] = pass_lst
#         df = single_trip_df.append(multi_trip_df)
    
#     #sort & re-define trip_id
#     df = df.sort_values('pickup_datetime').reset_index(drop=True)
#     df['trip_id'] = df.index+1
    
#     return df


# def process_rawtrips_file(df): 
#     df['trip_id'] = df.index + 1
#     df['trip_distance'] = scaled_haversine_dists(df['pickup_latitude'], 
#                                                  df['pickup_longitude'], 
#                                                  df['dropoff_latitude'], 
#                                                  df['dropoff_longitude'])
    
#     cols = ['trip_id', 'pickup_datetime', 'pickup_latitude', 
#             'pickup_longitude', 'dropoff_datetime', 'dropoff_latitude', 
#             'dropoff_longitude', 'trip_distance', 'passenger_count']
    
#     #remove 0-dist trips
#     df = df[df.trip_distance!=0]
    
#     #remove 0-time trips
#     df = df[(df.pickup_datetime != df.dropoff_datetime)]
    
#     return df[cols]


# def process_pooledtrips_file(df): 
#     df['trip_id'] = df.index + 1
#     df['trip_distance'] = scaled_haversine_dists(df['p_lat'], 
#                                                  df['p_lon'], 
#                                                  df['d_lat'], 
#                                                  df['d_lon'])
    
#     df.rename(columns={'pax_count': 'passenger_count', 
#                        'mean_pickup_datetime': 'pickup_datetime',
#                        'mean_dropoff_datetime': 'dropoff_datetime'}, inplace=True)
    
#     cols = ['trip_id', 'pickup_datetime', 'p_lat', 
#             'p_lon', 'dropoff_datetime', 'd_lat', 
#             'd_lon', 'trip_distance', 'passenger_count']
    
#     #remove 0-dist trips
#     df = df[df.trip_distance!=0]
    
#     #remove 0-time trips
#     df = df[(df.pickup_datetime != df.dropoff_datetime)]
    
#     return df[cols]

# def label_requests_to_report(df, min_dt, max_dt):
#     if isinstance(df['pickup_datetime'][0], str):
#         df['pickup_datetime'] = df['pickup_datetime'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'))
        
#     def report(val, min_dt=min_dt, max_dt=max_dt):
#         if (val >= min_dt) and (val<= max_dt):
#             report = True
#         else:
#             report = False
#         return report
    
#     df['report'] = df['pickup_datetime'].apply(report)
    
#     return df
    
