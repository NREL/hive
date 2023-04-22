from unittest import TestCase

from nrel.hive.util.time_helpers import read_time_string
from datetime import time


class TestUpdateRequests(TestCase):
    def test_read_time_string_good_time_values(self):
        t1 = read_time_string("00:00:00")
        t2 = read_time_string("23:59:59")
        t3 = read_time_string("7:00:00")
        t4 = read_time_string("13:00:00")

        self.assertEqual(t1, time(hour=0, minute=0, second=0))
        self.assertEqual(t2, time(hour=23, minute=59, second=59))
        self.assertEqual(t3, time(hour=7, minute=0, second=0))
        self.assertEqual(t4, time(hour=13, minute=0, second=0))

    def test_read_time_string_bad_time_values(self):
        with self.assertRaises(ValueError):
            read_time_string("24:00:00")
        with self.assertRaises(ValueError):
            read_time_string("-1:00:00")
        with self.assertRaises(ValueError):
            read_time_string("00:61:00")
        with self.assertRaises(ValueError):
            read_time_string("00:00:71")
