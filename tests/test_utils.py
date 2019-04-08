import sys
import os
import glob
import subprocess

import pandas as pd

from hive import utils

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def remove_files(directory):
    files = glob.glob(os.path.join(directory, '*'))
    for f in files:
        os.remove(f)

def make_dir(dir_path):
    if not os.path.isdir(dir_path):
        subprocess.run('mkdir {}'.format(dir_path), shell=True)


def test_generate_input_files():
    in_file = os.path.join(THIS_DIR, 'test_inputs','main.csv')
    out_path = os.path.join(THIS_DIR, 'test_inputs', '.scenarios')
    make_dir(out_path)
    remove_files(out_path)
    utils.generate_input_files(in_file=in_file, out_path=out_path)
    assert(os.path.isfile(os.path.join(out_path, 'test1_inputs.h5')))
    assert(os.path.isfile(os.path.join(out_path, 'test2_inputs.h5')))
    test1_inputs = pd.read_hdf(os.path.join(out_path, 'test1_inputs.h5'))
    test2_inputs = pd.read_hdf(os.path.join(out_path, 'test2_inputs.h5'))
    assert(test1_inputs.MAX_FLEET_SIZE == '200')
    assert(test2_inputs.CHARGING_SCENARIO == 'Station')

    in_file_transpose = os.path.join(THIS_DIR, 'test_inputs', 'main_transpose.csv')
    remove_files(out_path)
    utils.generate_input_files(in_file=in_file_transpose, out_path=out_path)
    assert(os.path.isfile(os.path.join(out_path, 'test1_inputs.h5')))
    assert(os.path.isfile(os.path.join(out_path, 'test2_inputs.h5')))
    test1_inputs = pd.read_hdf(os.path.join(out_path, 'test1_inputs.h5'))
    test2_inputs = pd.read_hdf(os.path.join(out_path, 'test2_inputs.h5'))
    assert(test1_inputs.MAX_FLEET_SIZE == '200')
    assert(test2_inputs.CHARGING_SCENARIO == 'Station')


    

    
