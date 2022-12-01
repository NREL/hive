from unittest import TestCase

from nrel.hive.config.network import Network
from nrel.hive.initialization.initialize_simulation import initialize
from nrel.hive.initialization.initialize_simulation_with_sampling import (
    initialize_simulation_with_sampling,
)
from nrel.hive.resources.mock_lobster import *


class TestInitializeSimulation(TestCase):
    def test_initialize_simulation(self):
        conf = mock_config().suppress_logging()

        sim, env = initialize(conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 1 base")

    def test_initialize_simulation_with_sampling(self):
        conf = (
            mock_config()
            ._replace(
                network=Network(
                    network_type="osm_network",
                    default_speed_kmph=40,
                )
            )
            .suppress_logging()
        )

        new_input = conf.input_config._replace(
            road_network_file=Path(
                resource_filename(
                    "nrel.hive.resources.scenarios.denver_downtown.road_network",
                    "downtown_denver_network.json",
                )
            )
        )

        conf = conf._replace(input_config=new_input)

        sim, env = initialize_simulation_with_sampling(
            config=conf,
            vehicle_count=20,
        )
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 2 bases")
