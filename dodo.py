import subprocess
import os
import sys
import glob
import re

import run

from hive import utils

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

PROFILE_OUTPUT_DIR = os.path.join('tests', 'profile_output')
PROFILE_FILES = glob.glob('hive/[!_]*.py') + ['run.py']

MAIN_INPUT_FILE = os.path.join('inputs', 'main.csv')
SCENARIO_PATH = os.path.join('inputs','.scenarios')

OUTPUT_DIR = 'outputs/'

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
    if not os.path.isdir(os.path.join(THIS_DIR, SCENARIO_PATH)):
        clean_msg('creating scenarios folder for input files..')
        subprocess.run('mkdir {}'.format(os.path.join(THIS_DIR, SCENARIO_PATH)), shell=True)
    if not os.path.isdir(os.path.join(THIS_DIR, OUTPUT_DIR)):
        clean_msg('creating output directory..')
        subprocess.run('mkdir {}'.format(os.path.join(THIS_DIR, OUTPUT_DIR)), shell=True)
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
            'verbosity': 2,
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
        output_file = PROFILE_OUTPUT_DIR + name + '.pstats'
        yield {
                'name': filepath,
                'actions': ['python -m cProfile -o {} {}'.format(output_file, filepath)],
                'file_dep': [filepath],
                'targets': [output_file],
                }
#TODO: Add functionality that only overwrites input files if the corresponding
#row in main.csv has changed.
def task_build_input_files():
    """
    Build input files from main.csv
    """
    if not os.path.isdir(os.path.join(THIS_DIR, OUTPUT_DIR)):
        clean_msg('creating output directory..')
        subprocess.run('mkdir {}'.format(os.path.join(THIS_DIR, OUTPUT_DIR)), shell=True)
    if not os.path.isdir(os.path.join(THIS_DIR, SCENARIO_PATH)):
        clean_msg('creating scenarios folder for input files..')
        subprocess.run('mkdir {}'.format(os.path.join(THIS_DIR, SCENARIO_PATH)), shell=True)
    return {
        'actions': [(
            utils.generate_input_files,
            [MAIN_INPUT_FILE, SCENARIO_PATH]
            )],
        'file_dep': [MAIN_INPUT_FILE],
    }


def task_run_simulation():
    """
    Run full simulation.
    """
    scenario_files = glob.glob(os.path.join(SCENARIO_PATH, '*.h5'))
    simulations = [(s, basename_stem(s)[:-7]) for s in scenario_files]

    for src, tag in simulations:
        save_path = os.path.join(OUTPUT_DIR, f'{tag}.h5')
        yield {
                'name': tag,
                'actions' : [
                    (run.run_simulation, [src, save_path]),
                    ],
                'file_dep': [src],
                'targets': [save_path],
                }
