r"""

##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/


Configurations for running hive
"""

SIMULATION_PERIOD_SECONDS = 60

#NOTE: all paths are relative to the root hive directory.

# Where hive will look for inputs. We don't recommend changing this.
IN_PATH = 'inputs/'

# Where hive will write outputs to.
OUT_PATH = 'outputs/'

VERBOSE = True
DEBUG = False

# Include all scenarios to run.
SCENARIOS = [
    'aus-test',
    'nyc-test',
]

RANDOM_SEED = 123

USE_OSRM = False
OSRM_SERVER = 'http://0.0.0.0:5000'
