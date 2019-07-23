import os
from distutils.dir_util import copy_tree
import subprocess
import sys

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def clean_msg(msg):
    print(msg)
    print()

def setup():
    env_on = sys.prefix.split('/')[-1] == 'hive'
    config_path = os.path.join(
            THIS_DIR, 'config.py'
            )
    default_config_path = os.path.join(
            THIS_DIR, '.config.default.py'
            )
    if not os.path.exists('config.py'):
        clean_msg('Setting up config files..')
        subprocess.run('cp .config.default.py config.py', shell=True)
    else:
        print('config.py already exists')
        ans = input('Update config file with default values? (y/[n]) ').lower()
        while ans not in ['y','n']:
            ans = input('please input y/n ')
        if ans == 'y':
            print('Updating config file..')
            subprocess.run('cp {} {}'.format(default_config_path, config_path), shell=True)
        print()

    #TODO: Make environment setup more robust for cross platform deployment.
    # if not os.path.exists(os.path.join(sys.prefix, 'envs/hive')) and not sys.prefix.split('/')[-1] == 'hive':
    #     print('Setting up virtual env')
    #     subprocess.run('conda env create -f environment.yml', shell=True)
    # else:
    #     print('Hive env already exists')
    #     ans = input('Update env? (y/[n]) ').lower()
    #     while ans not in ['y','n']:
    #         ans = input('Please input y/n ')
    #     if ans == 'y':
    #         if not env_on:
    #             subprocess.run('conda activate hive', shell=True)
    #         subprocess.run('conda env update -f=environment.yml', shell=True)

    print('Setting up default inputs..')
    input_path = os.path.join(THIS_DIR, 'inputs')
    default_input_path = os.path.join(input_path, '.inputs_default')
    copy_tree(default_input_path, input_path)

if __name__ == "__main__":
    setup()
