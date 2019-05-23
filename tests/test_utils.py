import sys
import os
import glob
import subprocess
import pandas as pd

from hive import utils

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def remove_files(directory):
    files = glob.glob(os.path.join(directory, '*'))
    for f in files:
        os.remove(f)

def make_dir(dir_path):
    if not os.path.isdir(dir_path):
        subprocess.run('mkdir {}'.format(dir_path), shell=True)
