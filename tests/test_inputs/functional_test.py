import unittest

# User Story

## Download repo from GitHub

## Run automated setup (python setup.py) to set default configs and build 
## conda (or pip) environment

## Update inputs for their scenario(s) - can select from defaults or customize
### vehicles in fleet
### operating area
### charging network
### cost of electricity
### fleet composition
### run setup - this is the only CRITICAL item for user configuration

## Run the simulation (could be many scenarios) (python run.py)
### Do not re-run identical scenarios in the same simulation
### Write outputs to a location specified in the config file

## Post-process simulation results - either use post-pro utilities or custom


class HiveTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_auto_setup(self):
        # run python setup.py in a sandbox with just miniconda
        ## create environment, set default configs

    def test_run_with_defaults(self):
        # User adds scenarios to the runSetup file from default input options

    def test_run_with_custom(self):
        # User defines their own inputs (i.e. vehicles, charge network, etc)
        ## then build runSetup file with custom inputs
    
    def test_no_rerun(self):
        # If user tries to re-run same scenarios in same simulation, run.py 
        # logic should skip it automatically

        




