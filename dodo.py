import subprocess
import os
import sys
import glob
import re

PROFILE_OUTPUT_DIR = 'tests/profile_output/'
PROFILE_FILES = glob.glob('hive/[!_]*.py') + ['run.py']

DOIT_CONFIG = {
        'default_tasks': [],
        }

def setup():
    env_on = sys.prefix.split('/')[-1] == 'hive'
    if not os.path.exists('config.py'):
        print('setting up config files')
        subprocess.run('cp config.default.py config.py', shell=True)
    else:
        print('config.py already exists')
        ans = input('update config file with default values? (y/[n]) ').lower()
        if ans == 'y':
            subprocess.run('cp config.defaults.py config.py', shell=True)
        else:
            print('please input y/n')
    if not os.path.exists(os.path.join(sys.prefix, 'envs/hive')) and not sys.prefix.split('/')[-1] == 'hive':
        print('setting up virtual env')
        subprocess.run('conda env create -f environment.yml', shell=True)
    else:
        print('hive env already exists')
        ans = input('update env? (y/[n]) ').lower()
        if ans == 'y':
            if not env_on:
                subprocess.run('conda activate hive', shell=True)
            subprocess.run('conda env update -f=environment.yml', shell=True)
        else:
            print('please input y/n.')
      
    
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
    Update conda environment.yml file and pip requirements.txt file.
    """
    for target, actions in [
            ('environment.yml', ['conda', 'env', 'export', '-n', 'hive']),
            ('requirements.txt', ['pip', 'freeze']),
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

