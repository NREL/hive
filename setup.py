import os
from distutils.dir_util import copy_tree
from shutil import copyfile
import subprocess
import sys

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def clean_msg(msg):
    print(msg)
    print()

def setup():
    config_path = os.path.join(
            THIS_DIR, 'config.py'
            )
    default_config_path = os.path.join(
            THIS_DIR, '.config.default.py'
            )
    if not os.path.exists('config.py'):
        clean_msg('Setting up config files..')
        copyfile('.config.default.py', 'config.py') #os-agnostic cp
    else:
        print('config.py already exists')
        ans = input('Update config file with default values? (y/n) ').lower()
        while ans not in ['y','n']:
            ans = input('please input y/n ')
        if ans == 'y':
            print('Updating config file..')
            copyfile('.config.default.py', 'config.py')
        print()

    #TODO: Add code to download default inputs from remote S3 bucket

    # print('Hive ships with a set of default inputs.')
    # ans = input('Should we copy these into the inputs directory? (y/n) ')
    # while ans not in ['y', 'n']:
    #     ans = input('please input y/n ')
    # if ans == 'y':
    #     print('Setting up default inputs..')
    #     input_path = os.path.join(THIS_DIR, 'inputs')
    #     default_input_path = os.path.join(input_path, '.inputs_default')
    #     copy_tree(default_input_path, input_path)

if __name__ == "__main__":
    setup()
