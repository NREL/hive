"""
Functions for calculating road network-level summary statistics. These are used
for estimated on-road VMT and average dispatch speeds.
"""
from haversine import haversine

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
    return total_vmt/total_short_path_dist


def calculate_average_driving_speed(reqs_df):
    """Calculates average driving speed for all trips in dataset
    """
    
    def row_hours(row):
        timedelta_s = (row['dropoff_time'] - row['pickup_time']).total_seconds()
        return timedelta_s / 3600

    hrs = reqs_df.apply(lambda row: row_hours(row), axis=1)
    total_hrs = hrs.sum()
    total_vmt = reqs_df['distance_miles'].sum()
    return total_vmt/total_hrs