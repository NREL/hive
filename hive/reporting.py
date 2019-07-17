"""
Functions for reporting vehicle-, fleet-, charge station-, & grid-level
results for simulation
"""

import pandas as pd

def calc_veh_stats(veh_fleet, vehicle_summary_file):
    for veh in veh_fleet:
        veh.dump_stats(vehicle_summary_file)

def calc_fleet_stats(output_file, vehicle_summary_file, reqs_df):
    veh_stats_df = pd.read_csv(vehicle_summary_file)

    fleet_stats = {}

    total_reqs = len(reqs_df)
    fleet_stats['total_requests'] = total_reqs
    reqs_filled = veh_stats_df['requests_filled'].sum()
    fleet_stats['fleet_requests_filled'] = int(reqs_filled)
    fleet_stats['pct_requests_filled'] = float(reqs_filled) / total_reqs * 100
    fleet_stats['mean_requests_filled'] = veh_stats_df['requests_filled'].mean()
    fleet_stats['max_requests_filled'] = int(veh_stats_df['requests_filled'].max())
    fleet_stats['min_requests_filled'] = int(veh_stats_df['requests_filled'].min())
    fleet_stats['std_requests_filled'] = veh_stats_df['requests_filled'].std()

    total_pass = reqs_df.passengers.sum()
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

    fleet_stats['fleet_request_vmt'] = float(veh_stats_df['request_vmt'].sum())
    fleet_stats['mean_request_vmt'] = veh_stats_df['request_vmt'].mean()
    fleet_stats['max_request_vmt'] = float(veh_stats_df['request_vmt'].max())
    fleet_stats['min_request_vmt'] = float(veh_stats_df['request_vmt'].min())
    fleet_stats['std_request_vmt'] = veh_stats_df['request_vmt'].std()

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

    fleet_stats['fleet_station_refuel_cnt'] = int(veh_stats_df['station_refuel_cnt'].sum())
    fleet_stats['mean_station_refuel_cnt'] = veh_stats_df['station_refuel_cnt'].mean()
    fleet_stats['max_station_refuel_cnt'] = int(veh_stats_df['station_refuel_cnt'].max())
    fleet_stats['min_station_refuel_cnt'] = int(veh_stats_df['station_refuel_cnt'].min())
    fleet_stats['std_station_refuel_cnt'] = veh_stats_df['station_refuel_cnt'].std()

    fleet_stats['fleet_station_refuel_hours'] = float(veh_stats_df['station_refuel_s'].sum()/3600)
    fleet_stats['mean_station_refuel_hours'] = veh_stats_df['station_refuel_s'].mean()/3600
    fleet_stats['max_station_refuel_hours'] = float(veh_stats_df['station_refuel_s'].max()/3600)
    fleet_stats['min_station_refuel_hours'] = float(veh_stats_df['station_refuel_s'].min()/3600)
    fleet_stats['std_station_refuel_hours'] = (veh_stats_df['station_refuel_s']/3600).std()

    fleet_stats['fleet_base_refuel_cnt'] = int(veh_stats_df['base_refuel_cnt'].sum())
    fleet_stats['mean_base_refuel_cnt'] = veh_stats_df['base_refuel_cnt'].mean()
    fleet_stats['max_base_refuel_cnt'] = int(veh_stats_df['base_refuel_cnt'].max())
    fleet_stats['min_base_refuel_cnt'] = int(veh_stats_df['base_refuel_cnt'].min())
    fleet_stats['std_base_refuel_cnt'] = veh_stats_df['base_refuel_cnt'].std()

    fleet_stats['fleet_base_refuel_hours'] = float(veh_stats_df['base_refuel_s'].sum()/3600)
    fleet_stats['mean_base_refuel_hours'] = veh_stats_df['base_refuel_s'].mean()/3600
    fleet_stats['max_base_refuel_hours'] = float(veh_stats_df['base_refuel_s'].max()/3600)
    fleet_stats['min_base_refuel_hours'] = float(veh_stats_df['base_refuel_s'].min()/3600)
    fleet_stats['std_base_refuel_hours'] = (veh_stats_df['base_refuel_s']/3600).std()

    fleet_stats['fleet_base_reserve_hours'] = float(veh_stats_df['base_reserve_s'].sum()/3600)
    fleet_stats['mean_base_reserve_hours'] = veh_stats_df['base_reserve_s'].mean()/3600
    fleet_stats['max_base_reserve_hours'] = float(veh_stats_df['base_reserve_s'].max()/3600)
    fleet_stats['min_base_reserve_hours'] = float(veh_stats_df['base_reserve_s'].min()/3600)
    fleet_stats['std_base_reserve_hours'] = (veh_stats_df['base_reserve_s']/3600).std()

    fleet_stats['fleet_idle_hours'] = float(veh_stats_df['idle_s'].sum()/3600)
    fleet_stats['mean_idle_hours'] = veh_stats_df['idle_s'].mean()/3600
    fleet_stats['max_idle_hours'] = float(veh_stats_df['idle_s'].max()/3600)
    fleet_stats['min_idle_hours'] = float(veh_stats_df['idle_s'].min()/3600)
    fleet_stats['std_idle_hours'] = (veh_stats_df['idle_s']/3600).std()

    with open(output_file, 'w') as f:
        def p(msg):
            print(msg, file=f)

        p("Fleet Summary")
        p("-" * 30)
        for key, val in fleet_stats.items():
            p(f'{key}: {val}')


def summarize_station_use(charg_stations):
    station_ids, refuel_cnts, refuel_energy_kwh = [], [], []
    for station in charg_stations:
        station_ids.append(station.ID)
        refuel_cnts.append(station.stats.charge_cnt)
        refuel_energy_kwh.append(station.stats.total_energy_kwh)

    station_summary_df = pd.DataFrame(data={'station_id': station_ids,
                                            'refuel_cnt': refuel_cnts,
                                            'refuel_energy_kwh': refuel_energy_kwh})

    return station_summary_df
