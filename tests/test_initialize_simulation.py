from unittest import TestCase

from hive.config.network import Network
from hive.initialization.initialize_simulation import initialize_simulation
from hive.initialization.initialize_simulation_with_sampling import initialize_simulation_with_sampling
from hive.resources.mock_lobster import *


class TestInitializeSimulation(TestCase):
    def test_initialize_simulation(self):
        conf = mock_config().suppress_logging()

        sim, env = initialize_simulation(conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 1 base")

    def test_initialize_simulation_with_filtering(self):
        conf = mock_config().suppress_logging()

        def filter_veh(v: Vehicle) -> bool:
            if v.id == 'v1':
                return False 

        def filter_base(b: Base) -> bool:
            if b.id == 'b1':
                return False 

        def filter_station(s: Station) -> bool:
            if s.id == 's1':
                return False 

        sim, env = initialize_simulation(
            conf,
            vehicle_filter=filter_veh,
            base_filter=filter_base,
            station_filter=filter_station,
        )

        self.assertIsNone(sim.vehicles.get('v1'), "should not have loaded vehicle v1")
        self.assertIsNone(sim.bases.get('b1'), "should not have loaded base b1")
        self.assertIsNone(sim.stations.get('s1'), "should not have loaded station s1")

    def test_initialize_simulation_with_sampling(self):
        conf = mock_config()._replace(network=Network(
            network_type='osm_network',
            default_speed_kmph=40,
        )).suppress_logging()

        new_input = conf.input_config._replace(road_network_file=Path(
            resource_filename("hive.resources.scenarios.denver_downtown.road_network",
                              "downtown_denver_network.json")))

        conf = conf._replace(input_config=new_input)

        sim, env = initialize_simulation_with_sampling(
            config=conf,
            vehicle_count=20,
        )
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 2 bases")
