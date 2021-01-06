from unittest import TestCase

from hive.initialization.initialize_simulation import initialize_simulation
from hive.initialization.initialize_simulation_with_sampling import initialize_simulation_with_sampling
from tests.mock_lobster import *


class TestInitializeSimulation(TestCase):

    def test_initialize_simulation(self):
        conf = mock_config()

        # deactivate logging to avoid writing log outputs from the test
        updated_global_config = conf.global_config._replace(log_states=False, log_run=False, log_events=False, log_instructions=False, log_stats=False)

        updated_conf = conf._replace(global_config=updated_global_config)

        sim, env = initialize_simulation(updated_conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 1 base")

    def test_initialize_simulation_with_sampling(self):
        conf = mock_config()

        # deactivate logging to avoid writing log outputs from the test
        updated_global_config = conf.global_config._replace(log_states=False, log_run=False, log_events=False, log_instructions=False, log_stats=False)

        updated_conf = conf._replace(global_config=updated_global_config)

        payload = initialize_simulation_with_sampling(
            config=updated_conf,
            vehicle_count=20,
            instruction_generators=(),
        )
        self.assertEqual(len(payload.s.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(payload.s.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(payload.s.bases), 2, "should have loaded 2 bases")
