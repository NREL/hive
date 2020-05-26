import glob
import os
import shutil
from unittest import TestCase

from hive.state.simulation_state.initialize_simulation import initialize_simulation
from tests.mock_lobster import *


class TestInitializeSimulation(TestCase):

    def test_initialize_simulation(self):
        conf = HiveConfig.build(
            {
                "sim": {
                    'start_time': 0,
                    'end_time': 10,
                    'timestep_duration_seconds': 1,
                    'sim_name': 'init_simulation_test_case',
                },
                "io": {
                    "file_paths": {
                        "requests_file": "denver_demo_requests.csv",
                        "rate_structure_file": "rate_structure.csv",
                        "vehicles_file": "denver_demo_vehicles.csv",
                        "bases_file": "denver_demo_bases.csv",
                        "stations_file": "denver_demo_stations.csv",
                        "mechatronics_file": "mechatronics.csv",
                        "geofence_file": "downtown_denver.geojson",

                    }
                }
            }
        )
        if not os.path.isdir(conf.scenario_output_directory):
            os.makedirs(conf.scenario_output_directory)

        sim, env = initialize_simulation(conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 3, "should have loaded 3 stations")
        self.assertEqual(len(sim.bases), 1, "should have loaded 1 base")

        # Clean up the output directories
        for d in glob.glob("init_simulation_test_case_*"):
            shutil.rmtree(d, ignore_errors=True)
