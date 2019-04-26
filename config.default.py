"""
Configurations for running hive over one or more scenario.
"""

SIMULATION_NAME = "Test Simulation"

# System
ARNAUD=False
if ARNAUD:
    N_PROCESSES = 40 #arg for multiprocessing.Pool

# In-Path
IN_PATH = 'inputs/'

# Out-Path
if ARNAUD:
    OUT_PATH = '/data/mbap_shared/'
else:
    OUT_PATH = 'outputs/' #local path

VERBOSE = True
DEBUG = True
