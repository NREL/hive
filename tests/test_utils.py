import sys
import pandas as pd
import os
sys.path.append('../hive/')

import utils

def test_generate_input_files():
    in_path = 'test_inputs/'
    out_path = 'test_inputs/.scenarios/'
    utils.generate_input_files(in_path=in_path, out_path=out_path)
    assert(os.path.isfile(out_path + 'test1_inputs.h5'))
    assert(os.path.isfile(out_path + 'test2_inputs.h5'))
    test1_inputs = pd.read_hdf(out_path + 'test1_inputs.h5')
    test2_inputs = pd.read_hdf(out_path + 'test2_inputs.h5')
    assert(test1_inputs.MAX_FLEET_SIZE == '200')
    assert(test2_inputs.CHARGING_SCENARIO == 'Station')
    

    
