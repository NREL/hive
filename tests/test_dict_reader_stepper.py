from unittest import TestCase

from pkg_resources import resource_filename

from hive.util.dict_reader_stepper import *


class TestDictReaderStepper(TestCase):

    def test_reading_up_to_a_time_bounds_should_leave_remaining_file_available(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time")
        stop_time = 12
        result = stepper.read_until_value(stop_time)
        self.assertEqual(len(result), 20, f"should have found 20 rows with departure time earlier than {stop_time}")
        self.assertEqual(float(stepper._iterator.history['departure_time']), stop_time, f"next has time {stop_time}")
        for row in result:
            self.assertLess(float(row['departure_time']), stop_time, f"should be less than {stop_time}")
        stepper.close()

    def test_reading_two_consecutive_times(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time")
        stop1 = 12
        stop2 = 14
        result1 = stepper.read_until_value(stop1)
        result2 = stepper.read_until_value(stop2)
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time [0, {stop1})")
        self.assertEqual(len(result2), 5, f"should have found 5 rows with departure time [{stop1}, {stop2})")
        for row in result1:
            self.assertLess(float(row['departure_time']), stop1, f"should be less than {stop1}")
        for row in result2:
            self.assertGreaterEqual(float(row['departure_time']), stop1, f"should be gte {stop1}")
            self.assertLess(float(row['departure_time']), stop2, f"should be less than {stop2}")
        stepper.close()

    def test_no_agents_after_end_of_file(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time")
        _ = stepper.read_until_value(9999998)
        result = stepper.read_until_value(9999999)
        self.assertEqual(len(result), 0, "should find no more agents after end of time")

    def test_no_second_file_reading_on_repeated_value(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time")
        stop = 12
        result1 = stepper.read_until_value(stop)
        result2 = stepper.read_until_value(stop)
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time earlier than {stop}")
        self.assertEqual(len(result2), 0, f"will not advance file by calling same stop value {stop}")

    def test_correct_management_of_stored_value_after_repeated_value(self):
        test_filename = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        stepper = DictReaderStepper.from_file(test_filename, "departure_time")
        stop1 = 12
        _ = stepper.read_until_value(stop1)
        _ = stepper.read_until_value(stop1)

        # show that second stop1 call means we should have done nothing since the first call
        stop2 = 13
        result = stepper.read_until_value(stop2)
        self.assertEqual(len(result), 1, f"should have found 20 rows with departure time earlier than {stop2}")
        self.assertEqual(float(stepper._iterator.history['departure_time']), stop2, f"next has time {stop2}")
        for row in result:
            self.assertGreaterEqual(float(row['departure_time']), stop1, f"should be gte {stop1}")
            self.assertLess(float(row['departure_time']), stop2, f"should be less than {stop2}")
