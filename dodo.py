import subprocess
import os
import sys
import glob
import re
import pandas as pd

import run
import config as cfg

from hive import utils

VERBOSE = 2 if cfg.VERBOSE else 0

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

IN_PATH = os.path.join(THIS_DIR, cfg.IN_PATH)
OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)

PROFILE_OUT_PATH = os.path.join('tests', 'profile_output')
PROFILE_FILES = glob.glob('hive/[!_]*.py') + ['run.py']

SCENARIO_PATH = os.path.join(IN_PATH, '.scenarios')

DOIT_CONFIG = {
        'default_tasks': [
            'build_input_files',
            'run_simulation',
            ],
        }

def basename_stem(path):
    return os.path.splitext(os.path.basename(path))[0]

def clean_msg(msg):
    print(msg)
    print()

def setup():
    env_on = sys.prefix.split('/')[-1] == 'hive'
    config_path = os.path.join(
            THIS_DIR, 'config.py'
            )
    default_config_path = os.path.join(
            THIS_DIR, 'config.default.py'
            )
    if not os.path.isdir(SCENARIO_PATH):
        clean_msg('creating scenarios folder for input files..')
        subprocess.run('mkdir {}'.format(SCENARIO_PATH), shell=True)
    if not os.path.isdir(OUT_PATH):
        clean_msg('creating output directory..')
        subprocess.run('mkdir {}'.format(OUT_PATH), shell=True)
    if not os.path.exists('config.py'):
        clean_msg('setting up config files')
        subprocess.run('cp config.default.py config.py', shell=True)
    else:
        print('config.py already exists')
        ans = input('update config file with default values? (y/[n]) ').lower()
        while ans not in ['y','n']:
            ans = input('please input y/n ')
        if ans == 'y':
            print('updating config file..')
            subprocess.run('cp {} {}'.format(default_config_path, config_path), shell=True)
        print()

    if not os.path.exists(os.path.join(sys.prefix, 'envs/hive')) and not sys.prefix.split('/')[-1] == 'hive':
        print('setting up virtual env')
        subprocess.run('conda env create -f environment.yml', shell=True)
    else:
        print('hive env already exists')
        ans = input('update env? (y/[n]) ').lower()
        while ans not in ['y','n']:
            ans = input('please input y/n ')
        if ans == 'y':
            if not env_on:
                subprocess.run('conda activate hive', shell=True)
            subprocess.run('conda env update -f=environment.yml', shell=True)

def run_actions(actions, target=None):
    if target == None:
        subprocess.run(actions)
    else:
        with open(target, 'w') as f:
            subprocess.run(actions, stdout=f)

def task_setup():
    """
    Setup project from sratch.
    """
    return {
            'actions': [setup],
            'verbosity': VERBOSE,
            }

def task_update_deps():
    """
    Update conda environment.yml file
    """
    for target, actions in [
            ('environment.yml', ['conda', 'env', 'export', '-n', 'hive']),
            ]:
        yield {
                'name': target,
                'actions': [(run_actions, [actions, target])],
                'targets': [target],
                'clean': True,
                }

def task_profile():
    """
    Profile each component using cProfile.
    """
    #TODO: Add functionality to generate svg call graph. gprof2dot, grpahviz
    #python gprof2dot.py -f pstats output.pstats | dot -Tsvg -o profile_graph.svg
    for filepath in PROFILE_FILES:
        name = re.split('[./]', filepath)[-2]
        output_file = PROFILE_OUT_PATH + name + '.pstats'
        yield {
                'name': filepath,
                'actions': ['python -m cProfile -o {} {}'.format(output_file, filepath)],
                'file_dep': [filepath],
                'targets': [output_file],
                }
#TODO: Add functionality that only reruns simulation if the corresponding
#row in main.csv has changed. Right now the .to_hdf function is producing
#unique md5 checksums for repeated runs of this fucntion with the same input.
def task_build_input_files():
    """
    Build input files from main.csv
    """
    if not os.path.isdir(SCENARIO_PATH):
        clean_msg('creating scenarios folder for input files..')
        subprocess.run('mkdir {}'.format(SCENARIO_PATH), shell=True)
    main_file = os.path.join(IN_PATH, 'main.csv')
    sim_df = pd.read_csv(main_file)
    for i, row in sim_df.iterrows():
        data = {}
        file_deps = [main_file]
        outfile = os.path.join(SCENARIO_PATH, '{}_inputs.h5'.format(row['SCENARIO_NAME']))
        charge_net_file = os.path.join(IN_PATH, 'charge_network', row['CHARGE_NET_FILE'])
        file_deps.append(charge_net_file)

        vehicle_ids = [{'name': c.replace("_NUM_VEHICLES", ""), 'num': row[c]} for c in row.index if 'VEH' in c]

        num_veh_types = len(vehicle_ids)
        assert num_veh_types > 0, 'Must have at least one vehicle type to run simulation.'
        row['NUM_VEHICLE_TYPES'] = str(num_veh_types)
        num_vehicles = 0

        for veh in vehicle_ids:
            num_vehicles += int(veh['num'])
            veh_file = os.path.join(IN_PATH, 'vehicles', '{}.csv'.format(veh['name']))
            file_deps.append(veh_file)
            veh_df = pd.read_csv(veh_file)
            veh_df['NUM_VEHICLES'] = veh['num']
            data[veh['name']] = veh_df.iloc[0]

        assert num_vehicles > 0, "Must have at least one vehicle to run simulation."
        row['TOTAL_NUM_VEHICLES'] = str(num_vehicles)

        data['charge_network'] = pd.read_csv(charge_net_file)
        data['main'] = row

        yield {
            'name': row['SCENARIO_NAME'],
            'actions': [(
                utils.save_to_hdf,
                [data, outfile]
                )],
            'file_dep': file_deps,
            'targets': [outfile],
            'verbosity': VERBOSE,
        }


def task_run_simulation():
    """
    Run full simulation.
    """
    if not os.path.isdir(OUT_PATH):
        clean_msg('creating output directory..')
        subprocess.run('mkdir {}'.format(OUT_PATH), shell=True)

    scenario_files = glob.glob(os.path.join(SCENARIO_PATH, '*.h5'))
    simulations = [(s, basename_stem(s)[:-7]) for s in scenario_files]

    for src, tag in simulations:
        outfile = os.path.join(OUT_PATH, f'{tag}.h5')
        yield {
                'name': tag,
                'actions' : [
                    (run.run_simulation, [src, outfile]),
                    ],
                'file_dep': [src],
                'targets': [outfile],
                'verbosity': VERBOSE,
                }
