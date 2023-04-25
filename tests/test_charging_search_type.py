from unittest import TestCase

from nrel.hive.custom_yaml import custom_yaml as yaml
from nrel.hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType


class TestChargingSearchType(TestCase):
    def test_yaml_repr(self):
        a = ChargingSearchType(1)
        yaml.add_representer(
            data_type=ChargingSearchType, representer=ChargingSearchType.yaml_representer
        )
        self.assertEqual(yaml.dump(a), "nearest_shortest_queue\n...\n")
