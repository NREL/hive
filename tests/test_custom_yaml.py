import logging
from pathlib import Path, PurePath
from unittest import TestCase

from nrel.hive.custom_yaml import custom_yaml as yaml
from nrel.hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from nrel.hive.model.sim_time import SimTime
from nrel.hive.model.vehicle.schedules.schedule_type import ScheduleType
from nrel.hive.reporting.report_type import ReportType

BASIC_TUPLE = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
BASIC_LIST = list(BASIC_TUPLE)

BASIC_SET = set([3, 2, 1, 0, 4, 6, 7, 5, 9, 8])


class TestClass(object):
    """An accessory class for use in tests without any YAML serialization methods."""

    def __str__(self):
        return "123abc123"


log = logging.getLogger(__name__)


class TestCustomYaml_Tuple(TestCase):
    def test_not_tagged_YAML(self):
        a = (1,)
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_tuple_like_list(self):
        self.assertEqual(
            yaml.dump(BASIC_LIST),
            yaml.dump(BASIC_TUPLE),
            "The custom YAML serializer is not treating a tuple like a YAML list.",
        )


class TestCustomYAML_Set(TestCase):
    def test_not_tagged_YAML(self):
        a = set([1])
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_set_like_list(self):
        self.assertEqual(
            yaml.dump(BASIC_LIST),
            yaml.dump(BASIC_SET),
            "The custom YAML serializer is not treating a set like a YAML list.",
        )


class TestCustomYAML_PathLib(TestCase):
    def test_purepath(self):
        ppath = PurePath("./test/")
        str_path = str(ppath)
        self.assertEqual(yaml.dump(str_path), yaml.dump(ppath))

    def test_path(self):
        path = Path("./test/")
        str_path = str(path)
        self.assertEqual(yaml.dump(str_path), yaml.dump(path))


class TestCustomYAML_ChargingSearchType(TestCase):
    def test_not_tagged_YAML(self):
        a = ChargingSearchType(1)
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_like_str(self):
        a = ChargingSearchType(1)
        self.assertEqual(yaml.dump(a), "nearest_shortest_queue\n...\n")


class TestCustomYAML_SimTime(TestCase):
    def test_not_tagged_YAML(self):
        a = SimTime.build(0)
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_like_iso_time_dynamic(self):
        a = SimTime.build(0)
        self.assertEqual(yaml.dump(a.as_iso_time()), yaml.dump(a))

    def test_like_iso_time_static(self):
        a = SimTime.build(0)
        self.assertEqual(yaml.dump(a.as_iso_time()), "'1970-01-01T00:00:00'\n")


class TestCustomYAML_ScheduleType(TestCase):
    def test_not_tagged_YAML(self):
        a = ScheduleType(0)
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_like_str(self):
        a = ScheduleType(0)
        self.assertEqual(yaml.dump(a), "time_range\n...\n")


class TestCustomYAML_ReportType(TestCase):
    def test_not_tagged_YAML(self):
        a = ReportType(1)
        self.assertNotEqual(yaml.dump(a)[0], "!", "YAML ! tag detected during serialization.")

    def test_like_str(self):
        a = ReportType(1)
        self.assertEqual(yaml.dump(a), "station_state\n...\n")


class TestCustomYAML_Generic(TestCase):
    def test_not_tagged_YAML(self):
        instance = TestClass()
        self.assertNotEqual(
            yaml.dump(instance)[0], "!", "YAML ! tag detected during serialization."
        )

    def test_warn_on_generic_serialization(self):
        for c in (TestClass, lambda: range(10)):
            instance = c()

            with self.assertLogs(level=logging.WARNING) as log_cm:
                a = yaml.dump(instance)
                print(a)

            warninglog = (
                "WARNING:nrel.hive.custom_yaml.custom_yaml:"
                + f"{instance.__class__} object was implicity serialized with `str(obj)`."
            )
            self.assertIn(
                warninglog,
                log_cm.output,
                msg="WARNING entry in log was not present when implicitly serializing an object.",
            )

    def test_generic_serialization_like_str(self):
        instance = TestClass()
        self.assertEqual(yaml.dump(str(instance)), yaml.dump(instance))
