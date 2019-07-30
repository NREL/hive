import pandas as pd
import sys
import glob
import os
import pickle
import csv
import shutil

class Clock:
    def __init__(self):
        self.now = 0
    def __next__(self):
        self.now += 1

def save_to_hdf(data, outfile):
    for key, val in data.items():
        val.to_hdf(outfile, key=key)

def save_to_pickle(data, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(data, f)

def initialize_log(fieldnames, logfile):
    with open(logfile, 'w+') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

def write_log(data, fieldnames, logfile):
    """
    Writes data to specified logfile. Enforces specified fieldnames schema to
    ensure writes are not improperly ordered.
    """
    assert type(data) == type(dict()), 'log data must be a dictionary.'
    with open(logfile, 'a') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(data)


def build_output_dir(scenario_name, root_path):
    scenario_output = os.path.join(root_path, scenario_name)
    if os.path.isdir(scenario_output):
        shutil.rmtree(scenario_output)
    os.makedirs(scenario_output)
    os.makedirs(os.path.join(scenario_output, 'logs'))
    os.makedirs(os.path.join(scenario_output, 'summaries'))

def assert_constraint(param, val, CONSTRAINTS, context=""):
    """
    Helper function to assert constraints at runtime.

    between:        Check that value is between upper and lower bounds exclusive
    between_incl:   Check that value is between upper and lower bounds inclusive
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
    elif condition == 'between_incl':
        assert val >= CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
        assert val <= CONSTRAINTS[param][2], \
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
