"""
Functions that prepare raw data for simulation
"""

import sys
import glob
import pandas as pd
from time import mktime
from datetime import datetime
from haversine import haversine
sys.path.append('../')
import inputs as inpt
import random 
import numpy as np

def gen_synth_pax_cnt():
    """Randomly assigns passenger count from real-world distribution measured
    in 2016(?) in Denver, CO by Henao (NREL)."""
    occ_distr = [1] * 743 + [2] * 175 + [3] * 58 + [4] * 24 #from Henao
    pax = random.choice(occ_distr)
    
    return pax

def load_requests(reqs_path):
        """Loads, combines, and sorts request csvs by pickup time 
        into a Pandas DataFrame
        """
    
        req_files = glob.glob(reqs_path+'*.csv')
        df_from_each_file = (pd.read_csv(f) for f in req_files)
        reqs_df = pd.concat(df_from_each_file, ignore_index=True)
        reqs_df['pickup_time'] = reqs_df['pickup_time'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        reqs_df['dropoff_time'] = reqs_df['dropoff_time'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
        reqs_df.sort_values('pickup_time', inplace=True)

        if 'passengers' not in reqs_df.columns: #apply real-world pax distr
            pax = [gen_synth_pax_cnt() for i in range(len(reqs_df))]
            reqs_df['passengers'] = pax
        
        return reqs_df



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
    
