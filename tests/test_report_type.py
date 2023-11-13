from unittest import TestCase

from nrel.hive.custom_yaml import custom_yaml as yaml
from nrel.hive.reporting.report_type import ReportType


class TestReportType(TestCase):
    def test_yaml_repr(self):
        yaml.add_representer(data_type=ReportType, representer=ReportType.yaml_representer)
        self.assertEqual("station_state\n...\n", yaml.dump(ReportType.from_string("station_state")))

    def test_ReportType_ordering_dynamic(self):
        members = [m for m in ReportType]
        name_then_sort = sorted([m.name for m in members])
        sort_then_name = [m.name for m in sorted(members)]
        self.assertEqual(name_then_sort, sort_then_name, "ReportType sorting invalid.")

    def test_ReportType_ordering_static(self):
        a = ReportType.from_string("station_state")
        b = ReportType.from_string("driver_state")
        self.assertLess(b, a, "ReportType sorting invalid.")

    def test_ReportType_lt_raise(self):
        class GenericClass:
            @property
            def name(self):
                return "abc"

        a = ReportType.from_string("station_state")
        b = GenericClass()
        with self.assertRaises(TypeError):
            x = a < b
