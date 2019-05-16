import unittest
import subprocess

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
    @classmethod
    def setUpClass(cls):
        # Copy default simulation inputs into /tests dir
        subprocess.run("cp -r .inputs_default /tests/inputs")
        
        # Define any class variables 


    @classmethod
    def tearDownClass(cls):
        # Cleanup all input and output directories in /tests dir
        subprocess.run("rm -r  /tests/inputs")
        subprocess.run("rm -r  /tests/outputs")
    

    def test_run_with_defaults(self):
        # User adds scenarios to the runSetup file from default input options
        ## TODO: collapse sub directories in test_inputs/
        ## TODO: reformat some test_inputs (i.e. main.csv)
        subprocess.run(["python", "run.py"])

    # Parallel v sequential

    # fresh runs v cached runs - within same scenario

    # test outputs - file presence, location, and sizes

    #TODO: Add post processing capabilities (inspiration from MM)

if __name__ == '__main__':
    unittest.main(warnings='ignore')        




