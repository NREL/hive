from unittest import TestCase

from hive.state.simulation_state.initialize_simulation import initialize_simulation
from tests.mock_lobster import *


class TestInitializeSimulation(TestCase):

    def test_initialize_simulation(self):
        conf = mock_config()

        updated_global_config = conf.global_config._replace(log_sim=False, log_run=False)
        updated_conf = conf._replace(global_config=updated_global_config)

        sim, env = initialize_simulation(updated_conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 3, "should have loaded 3 stations")
        self.assertEqual(len(sim.bases), 1, "should have loaded 1 base")
