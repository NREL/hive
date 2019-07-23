"""
Configurations for running hive over one or more scenario.
"""

# Each simulation gets a sub directory in the outputs folder. If you don't
# to overwrite outputs, specify a new simulation name here.
SIMULATION_NAME = "Test Simulation"

#NOTE: all paths are relative to the root hive directory.

# Where hive will look for inputs. We don't recommend changing this.
IN_PATH = 'inputs/'

# Where hive will write outputs to.
OUT_PATH = 'outputs/'

VERBOSE = True
DEBUG = False 
