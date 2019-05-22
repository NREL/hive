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

def assert_constraint(param, val, CONSTRAINTS, context=""):
    """
    Helper function to assert constraints at runtime.

    between:        Check that value is between upper and lower bounds exclusive
    greater_than:   Check that value is greater than lower bound exclusive
    less_than:      Check that value is less than upper bound exclusive
    in_set:         Check that value is in a set
    """
    condition = CONSTRAINTS[param][0]

    if condition == 'between':
        assert val > CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
        assert val < CONSTRAINTS[param][2], \
            "Context: {} | Param {}:{} is over high limit {}"\
            .format(context, param, val, CONSTRAINTS[param][2])
    elif condition == 'greater_than':
        assert val > CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
    elif condition == 'less_than':
        assert val < CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is over high limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
    elif condition == 'in_set':
        assert val in CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} must be from set {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
