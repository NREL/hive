import pandas as pd
import sys
import glob

sys.path.append('../')
import config as cfg

def generate_input_files(in_path='../inputs/', out_path='../inputs/.scenarios/'):
    sim_df = pd.read_csv(in_path + 'main.csv', header=None)
    if 'SCENARIO_NAME' and 'MAX_FLEET_SIZE' in sim_df[0].values:
        sim_df = sim_df.T
    sim_df = sim_df.rename(columns=sim_df.iloc[0]).drop(0).reset_index(drop=True)
    for i, row in sim_df.iterrows():
        row.to_hdf(out_path + '{}_inputs.h5'.format(row['SCENARIO_NAME']), key='s', mode='w')
        

