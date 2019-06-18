"""
Functions for reporting vehicle-, fleet-, charge station-, & grid-level
results for simulation
"""

import pandas as pd

def calc_veh_stats(veh_fleet, summary_file):
    for veh in veh_fleet:
        veh.dump_stats(summary_file)

def calc_fleet_stats(veh_stats_df, req_queue):
    fleet_stats = {}

    total_reqs = len(req_queue)
    fleet_stats['total_requests'] = total_reqs
    reqs_filled = veh_stats_df['requests_filled'].sum()
    fleet_stats['fleet_requests_filled'] = int(reqs_filled)
    fleet_stats['pct_requests_filled'] = float(reqs_filled) / total_reqs * 100
    fleet_stats['mean_requests_filled'] = veh_stats_df['requests_filled'].mean()
    fleet_stats['max_requests_filled'] = int(veh_stats_df['requests_filled'].max())
    fleet_stats['min_requests_filled'] = int(veh_stats_df['requests_filled'].min())
    fleet_stats['std_requests_filled'] = veh_stats_df['requests_filled'].std()

    total_pass = req_queue[:,8].sum()
    fleet_stats['total_passenger_requests'] = total_pass
    pass_del = veh_stats_df['passengers_delivered'].sum()
    fleet_stats['fleet_passengers_delivered'] = int(pass_del)
    fleet_stats['pct_passengers_delivered'] = float(pass_del) / total_pass * 100
    fleet_stats['mean_passengers_delivered'] = veh_stats_df['passengers_delivered'].mean()
    fleet_stats['max_passengers_delivered'] = int(veh_stats_df['passengers_delivered'].max())
    fleet_stats['min_passengers_delivered'] = int(veh_stats_df['passengers_delivered'].min())
    fleet_stats['std_passengers_delivered'] = veh_stats_df['passengers_delivered'].std()

    fleet_stats['mean_pct_time_trip'] = veh_stats_df['pct_time_trip'].mean()
    fleet_stats['max_pct_time_trip'] = float(veh_stats_df['pct_time_trip'].max())
    fleet_stats['min_pct_time_trip'] = float(veh_stats_df['pct_time_trip'].min())
    fleet_stats['std_pct_time_trip'] = float(veh_stats_df['pct_time_trip'].mean())

    fleet_stats['fleet_trip_vmt'] = float(veh_stats_df['trip_vmt'].sum())
    fleet_stats['mean_trip_vmt'] = veh_stats_df['trip_vmt'].mean()
    fleet_stats['max_trip_vmt'] = float(veh_stats_df['trip_vmt'].max())
    fleet_stats['min_trip_vmt'] = float(veh_stats_df['trip_vmt'].min())
    fleet_stats['std_trip_vmt'] = veh_stats_df['trip_vmt'].std()

    fleet_stats['fleet_dispatch_vmt'] = float(veh_stats_df['dispatch_vmt'].sum())
    fleet_stats['mean_dispatch_vmt'] = veh_stats_df['dispatch_vmt'].mean()
    fleet_stats['max_dispatch_vmt'] = float(veh_stats_df['dispatch_vmt'].max())
    fleet_stats['min_dispatch_vmt'] = float(veh_stats_df['dispatch_vmt'].min())
    fleet_stats['std_dispatch_vmt'] = veh_stats_df['dispatch_vmt'].std()

    fleet_stats['fleet_total_vmt'] = float(veh_stats_df['total_vmt'].sum())
    fleet_stats['mean_total_vmt'] = veh_stats_df['total_vmt'].mean()
    fleet_stats['max_total_vmt'] = float(veh_stats_df['total_vmt'].max())
    fleet_stats['min_total_vmt'] = float(veh_stats_df['total_vmt'].min())
    fleet_stats['std_total_vmt'] = veh_stats_df['total_vmt'].std()

    fleet_stats['fleet_refuel_count'] = int(veh_stats_df['refuel_count'].sum())
    fleet_stats['mean_refuel_count'] = veh_stats_df['refuel_count'].mean()
    fleet_stats['max_refuel_count'] = int(veh_stats_df['refuel_count'].max())
    fleet_stats['min_refuel_count'] = int(veh_stats_df['refuel_count'].min())
    fleet_stats['std_refuel_count'] = veh_stats_df['refuel_count'].std()

    fleet_stats['fleet_refuel_hours'] = float(veh_stats_df['refuel_seconds'].sum()/3600)
    fleet_stats['mean_refuel_hours'] = veh_stats_df['refuel_seconds'].mean()/3600
    fleet_stats['max_refuel_hours'] = float(veh_stats_df['refuel_seconds'].max()/3600)
    fleet_stats['min_refuel_hours'] = float(veh_stats_df['refuel_seconds'].min()/3600)
    fleet_stats['std_refuel_hours'] = (veh_stats_df['refuel_seconds']/3600).std()

    fleet_stats['fleet_idle_hours'] = float(veh_stats_df['idle_seconds'].sum()/3600)
    fleet_stats['mean_idle_hours'] = veh_stats_df['idle_seconds'].mean()/3600
    fleet_stats['max_idle_hours'] = float(veh_stats_df['idle_seconds'].max()/3600)
    fleet_stats['min_idle_hours'] = float(veh_stats_df['idle_seconds'].min()/3600)
    fleet_stats['std_idle_hours'] = (veh_stats_df['idle_seconds']/3600).std()

    return fleet_stats

def summarize_station_use(charg_stations):
    station_ids, refuel_cnts = [], []
    for station in charg_stations:
        station_ids.append(station.station_id)
        refuel_cnts.append(station.refuel_cnt)

    station_summary_df = pd.DataFrame(data={'station_id': station_ids,
                                      'refuel_count': refuel_cnts})

    return station_summary_df
