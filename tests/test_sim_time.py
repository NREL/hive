from unittest import TestCase

from nrel.hive.custom_yaml import custom_yaml as yaml
from nrel.hive.model.sim_time import SimTime


class TestSimTime(TestCase):
    def test_yaml_repr(self):
        yaml.add_representer(data_type=SimTime, representer=SimTime.yaml_representer)
        self.assertEqual("'1970-01-01T00:00:00'\n", yaml.dump(SimTime.build(0)))
