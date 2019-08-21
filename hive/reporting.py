"""
Functions for reporting vehicle-, fleet-, charge station-, & grid-level
results for simulation
"""

import pandas as pd
import csv
import os

def generate_logs(objects, log_path, context):
    keys = objects[0].history[0].keys()
    for item in objects:
        filename = os.path.join(log_path, f'{context}_{item.ID}_history.csv')
        with open(filename, 'w') as f:
            writer = csv.DictWriter(f, keys)
            writer.writeheader()
            writer.writerows(item.history)


def summarize_station_use(stations_dict, bases_dict, station_summary_file):
    stations = list(stations_dict.values())
    bases = list(bases_dict.values())
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
