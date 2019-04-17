import pandas as pd
import sys
import glob
import os

sys.path.append('../')
import config as cfg

def generate_input_files(in_file, out_path):
    if cfg.VERBOSE: print("gererating input files..")
    sim_df = pd.read_csv(in_file, header=None)
    if 'SCENARIO_NAME' and 'MIN_ALLOWED_SOC' in sim_df[0].values:
        sim_df = sim_df.T
    sim_df = sim_df.rename(columns=sim_df.iloc[0]).drop(0).reset_index(drop=True)
    for i, row in sim_df.iterrows():
        row.to_hdf(os.path.join(out_path, '{}_inputs.h5'.format(row['SCENARIO_NAME'])), key='s', mode='w')
