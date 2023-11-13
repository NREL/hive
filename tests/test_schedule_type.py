from unittest import TestCase

from nrel.hive.custom_yaml import custom_yaml as yaml
from nrel.hive.model.vehicle.schedules.schedule_type import ScheduleType


class TestSimTime(TestCase):
    def test_yaml_repr(self):
        yaml.add_representer(data_type=ScheduleType, representer=ScheduleType.yaml_representer)
        self.assertEqual("time_range\n...\n", yaml.dump(ScheduleType(0)))
