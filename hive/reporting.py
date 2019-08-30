"""
Functions for reporting vehicle-, fleet-, charge station-, & grid-level
results for simulation
"""

import pandas as pd
import csv
import os
import glob

def generate_logs(objects, log_path, context):
    """
    Generates logs for a list of hive objects.

    Parameters
    ----------
    objects: list
        list of hive objects for which to write logs.
    lob_path: str
        filepath for where to write the logs to.
    context: str
        string representing the type of object that is being passed.
    """
    #TODO: Make this function more robust by ensuring all objects have same keys.
    keys = objects[0].history[0].keys()
    for item in objects:
        filename = os.path.join(log_path, f'{context}_{item.ID}_history.csv')
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, keys)
            writer.writeheader()
            writer.writerows(item.history)


def summarize_station_use(stations, bases, station_summary_file):
    """
    Generates station level summary statistics.

    Parameters
    ----------
    stations: list
        list of station objects.
    bases: list
        list of bases objects.
    station_summary_file: str
        filepath for where to write station summary stats.
    """

    #TODO: Make this rely on station and base log files so it can be run after a sim.
    charg_stations = stations + bases
    station_ids, refuel_cnts, refuel_energy_kwh = [], [], []
    for station in charg_stations:
        station_ids.append(station.ID)
        refuel_cnts.append(station.stats['charge_cnt'])
        refuel_energy_kwh.append(station.stats['total_energy_kwh'])

    station_summary_df = pd.DataFrame(data={'station_id': station_ids,
                                            'refuel_cnt': refuel_cnts,
                                            'refuel_energy_kwh': refuel_energy_kwh})

    station_summary_df.to_csv(station_summary_file, index=False)

def summarize_fleet_stats(vehicle_log_path, summary_path):
    """
    Generates fleet level summary statistics.

    Parameters
    ----------
    vehicle_log_path: str
        filepath to where vehicle logs are written.
    summary_path: str
        path to where to write the fleet summary stats.
    """

    # VMT Summary
    drop_columns = ['Charging at Station', 'Idle', 'Reserve']
    all_vehicle_logs = glob.glob(os.path.join(vehicle_log_path, '*.csv'))
    fleet_df = pd.concat((pd.read_csv(file) for file in all_vehicle_logs))
    outfile = os.path.join(summary_path, 'fleet_vmt_summary.csv')
    fleet_df.groupby('activity').sum()['step_distance_mi']\
        .drop(drop_columns).to_csv(outfile, header=True)

    # Time Summary
    outfile = os.path.join(summary_path, 'fleet_time_summary.csv')
    fleet_df.groupby('activity').count()['sim_time'].to_csv(outfile, header=True)
