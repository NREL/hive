from unittest import TestCase

from pkg_resources import resource_filename
from datetime import datetime
from typing import Callable

from hive.util.dict_reader_stepper import *


class TestDictReaderStepper(TestCase):
    def _generate_stop_condition(self, stop_time: int) -> Callable:
        def stop_condition(value: str) -> bool:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return dt.timestamp() < stop_time
        return stop_condition

    def test_reading_up_to_a_time_bounds_should_leave_remaining_file_available(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stop_time = 25920
        stop_condition = self._generate_stop_condition(stop_time)
        stepper = DictReaderStepper.from_file(test_filename, "departure_time", self._generate_stop_condition(0))
        result = tuple(stepper.read_until_stop_condition(stop_condition))
        self.assertEqual(len(result), 20, f"should have found 20 rows with departure time earlier than {stop_time}")
        self.assertEqual(
            datetime.strptime(stepper._iterator.history['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
            stop_time,
            f"next has time {stop_time}"
        )
        for row in result:
            self.assertLess(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop_time,
                f"should be less than {stop_time}"
            )
        stepper.close()

    def test_reading_two_consecutive_times(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time", self._generate_stop_condition(0))
        stop1 = 25920
        stop2 = 26040
        result1 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))
        result2 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop2)))
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time [0, {stop1})")
        self.assertEqual(len(result2), 5, f"should have found 5 rows with departure time [{stop1}, {stop2})")
        for row in result1:
            self.assertLess(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop1,
                f"should be less than {stop1}")
        for row in result2:
            self.assertGreaterEqual(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop1,
                f"should be gte {stop1}")
            self.assertLess(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop2,
                f"should be less than {stop2}")
        stepper.close()

    def test_no_agents_after_end_of_file(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time", self._generate_stop_condition(0))
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(9999998)))
        result = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(9999999)))
        self.assertEqual(len(result), 0, "should find no more agents after end of time")

    def test_no_second_file_reading_on_repeated_value(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time", self._generate_stop_condition(0))
        stop = 25920
        result1 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop)))
        result2 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop)))
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time earlier than {stop}")
        self.assertEqual(len(result2), 0, f"will not advance file by calling same stop value {stop}")

    def test_correct_management_of_stored_value_after_repeated_value(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time", self._generate_stop_condition(0))
        stop1 = 25920
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))

        # show that second stop1 call means we should have done nothing since the first call
        stop2 = 25980
        result = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop2)))
        self.assertEqual(len(result), 1, f"should have found 20 rows with departure time earlier than {stop2}")
        self.assertEqual(
            datetime.strptime(stepper._iterator.history['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
            stop2,
            f"next has time {stop2}"
        )
        for row in result:
            self.assertGreaterEqual(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop1,
                f"should be gte {stop1}"
            )
            self.assertLess(
                datetime.strptime(row['departure_time'], "%Y-%m-%d %H:%M:%S").timestamp(),
                stop2,
                f"should be less than {stop2}")
