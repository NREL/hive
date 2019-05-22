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
        subprocess.run("mkdir /tests/inputs")
        subprocess.run("cp -r .inputs_default /tests/inputs")
        
        # Define any class variables 


    @classmethod
    def tearDownClass(cls):
        # Cleanup all input and output directories in /tests dir
        subprocess.run("rm -r  /tests/inputs")
        subprocess.run("rm -r  /tests/outputs")


    def test_cpu_scaling(self):
        subprocess.run(["python", "run.py","n_jobs=auto"])
        subprocess.run(["python", "run.py","n_jobs=1"])
        subprocess.run(["python", "run.py","n_jobs=2"])
        subprocess.run(["python", "run.py","n_jobs=3"])


    def test_fresh_run(self):
        pass
    

    def test_customize_scenario(self):
        # testing non-default inputs
        # TODO: Modify run setup file to include previous runs and new customs
        pass
    

    def test_cached_runs(self):
        pass


    def test_outputs(self):
        # check for file presence, location, and expected sizes based on inputs
        # logging
        pass


    #TODO: Add post processing capabilities (inspiration/input from MM)

if __name__ == '__main__':
    unittest.main()