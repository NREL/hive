import pandas as pd
import sys
import glob
import os
import pickle

def save_to_hdf(data, outfile):
    for key, val in data.items():
        val.to_hdf(outfile, key=key)

def save_to_pickle(data, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(data, f)

def init_failure_log():
    failure_log  = {}
    failure_log['active_max_dispatch'] = 0
    failure_log['active_time'] = 0
    failure_log['active_battery'] = 0
    failure_log['inactive_time'] = 0
    failure_log['inactive_battery'] = 0
    return failure_log

def assert_constraint(param, val, CONSTRAINTS):
    condition = CONSTRAINTS[param][0]

    if condition == 'between':
        assert val > CONSTRAINTS[param][1], "Param {}:{} is out of bounds {}".format(param, val, CONSTRAINTS[param])
        assert val < CONSTRAINTS[param][2], "Param {}:{} is out of bounds {}".format(param, val, CONSTRAINTS[param])
