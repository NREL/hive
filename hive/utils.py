import sys
import glob
import os
import pickle
import csv
import shutil

sys.path.append('..')
import config as cfg

class Clock:
    """
    Iterator to store simulation time information.

    Parameters
    ----------
    timestep_s: int
        amount of seconds that one simulation time step represents.
    """
    def __init__(self, timestep_s, datetime_steps):
        self.now = 0
        self.TIMESTEP_S = timestep_s
        self._DATETIME_STEPS = datetime_steps
    def __next__(self):
        self.now += 1
    def get_time(self):
        return self._DATETIME_STEPS[self.now]

def info(msg):
    if cfg.VERBOSE:
        print(f"[info] {msg}")

def name(path):
    return os.path.splitext(os.path.basename(path))[0]

def progress_bar(
            iteration,
            total,
            prefix = '[info] Progress:',
            suffix = 'Complete',
            decimals = 1,
            length = 50,
            fill = '█'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    sys.stdout.write('%s |%s| %s%% %s\r' % (prefix, bar, percent, suffix))
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')


def save_to_hdf(data, outfile):
    """
    Function to save data to hdf5.
    """
    for key, val in data.items():
        val.to_hdf(outfile, key=key)

def save_to_pickle(data, outfile):
    """
    Function to save data to pickle.
    """
    with open(outfile, 'wb') as f:
        pickle.dump(data, f)


def build_output_dir(scenario_name, root_path):
    """
    Function to build scenario level output directory in root output directory.
    """
    scenario_output = os.path.join(root_path, scenario_name)
    if os.path.isdir(scenario_output):
        shutil.rmtree(scenario_output)
    os.makedirs(scenario_output)
    file_paths = {}
    log_path = os.path.join(scenario_output, 'logs')
    file_paths['log_path'] = log_path
    file_paths['summary_path'] = os.path.join(scenario_output, 'summaries')
    file_paths['vehicle_path'] = os.path.join(log_path, 'vehicles')
    file_paths['station_path'] = os.path.join(log_path, 'stations')
    file_paths['base_path'] = os.path.join(log_path, 'bases')
    file_paths['dispatcher_path'] = os.path.join(log_path, 'dispatcher')
    os.makedirs(file_paths['log_path'])
    os.makedirs(file_paths['vehicle_path'])
    os.makedirs(file_paths['station_path'])
    os.makedirs(file_paths['base_path'])
    os.makedirs(file_paths['dispatcher_path'])
    os.makedirs(file_paths['summary_path'])

    return file_paths

def assert_constraint(param, val, CONSTRAINTS, context=""):
    """
    Helper function to assert constraints at runtime.

    Parameters
    ----------
    param: str
        parameter of interest to check against constraint.
    val: int, float, str
        value of parameter that needs checking.
    CONSTRAINTS: dict
        dictionary of the constraints from hive.constraints.
    context: str
        context to inform the function what time of checking to perform.

    Notes
    -----

    Valid values for context:

    * between:        Check that value is between upper and lower bounds exclusive
    * between_incl:   Check that value is between upper and lower bounds inclusive
    * greater_than:   Check that value is greater than lower bound exclusive
    * less_than:      Check that value is less than upper bound exclusive
    * in_set:         Check that value is in a set
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
