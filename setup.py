import os
from shutil import copyfile
import sys

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(THIS_DIR, 'inputs')
SCENARIO_PATH = os.path.join(INPUT_PATH, 'scenarios')

sys.path.append(INPUT_PATH)
from generate_scenarios import build_scenarios

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

    print('Generating default scenarios..')
    if not os.path.exists(SCENARIO_PATH):
        os.makedirs(SCENARIO_PATH)
    build_scenarios()


if __name__ == "__main__":
    setup()
