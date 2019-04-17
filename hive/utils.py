import pandas as pd
import sys
import glob
import os

sys.path.append('../')
import config as cfg

def generate_input_files(in_path, out_path):
    in_file = os.path.join(in_path, 'main.csv')
    if cfg.VERBOSE: print("gererating input files..")
    sim_df = pd.read_csv(in_file, header=None).T
    sim_df = sim_df.rename(columns=sim_df.iloc[0]).drop(0).reset_index(drop=True)
    for i, row in sim_df.iterrows():
        filename = os.path.join(out_path, '{}_inputs.h5'.format(row['SCENARIO_NAME']))
        vehicle_ids = [{'name': c.replace("_NUM_VEHICLES", ""), 'num': row[c]} for c in sim_df.columns if 'VEH' in c]
        num_veh_types = len(vehicle_ids)
        assert num_veh_types > 0, 'Must have at least one vehicle type to run simulation.'
        row['NUM_VEHICLE_TYPES'] = str(num_veh_types)
        num_vehicles = 0
        for veh in vehicle_ids:
            num_vehicles += int(veh['num'])
            veh_df = pd.read_csv(os.path.join(in_path, 'vehicles', '{}.csv'.format(veh['name'])), header=None).T
            veh_df = veh_df.rename(columns=veh_df.iloc[0]).drop(0).reset_index(drop=True)
            veh_df['NUM_VEHICLES'] = veh['num']
            veh_df.iloc[0].to_hdf(filename, key=veh['name'])
        assert num_vehicles > 0, "Must have at least one vehicle to run simulation."
        row['TOTAL_NUM_VEHICLES'] = str(num_vehicles)
        row.to_hdf(filename, key='main')
