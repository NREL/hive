"""
Configurations for running hive over one or more scenario.
"""
# System
ARNAUD=False
if ARNAUD:
    N_PROCESSES = 40 #arg for multiprocessing.Pool

# In-Paths
IN_PATH = 'inputs/'
OPERATING_AREA_PATH = 'inputs/operating_area/rideaustin/'
REQUEST_PATH = 'inputs/requests/rideaustin/'

# Out-Paths
if ARNAUD:
    OUT_PATH = '/data/mbap_shared/'
else:
    OUT_PATH = 'outputs/' #local path

VERBOSE = True
DEBUG = True

# Set to True for development.
DEV = True
