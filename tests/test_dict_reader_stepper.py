from unittest import TestCase

from pkg_resources import resource_filename

from hive.model.sim_time import SimTime
from hive.util.iterators import *


class TestDictReaderStepper(TestCase):
    def _generate_stop_condition(self, stop_time: SimTime) -> Callable:
        def stop_condition(value: SimTime) -> bool:
            r = value < stop_time
            return r

        return stop_condition

    def test_invalid_file(self):
        test_filename = "invalid#Q(F*E:/file/location"
        error, stepper = DictReaderStepper.build(test_filename, "blargrog", parser=SimTime.build)
        self.assertIsNone(stepper)
        self.assertIsInstance(error, Exception)

    def test_reading_up_to_a_time_bounds_should_leave_remaining_file_available(self):
        test_filename = resource_filename("hive.resources.scenarios.denver_downtown.requests",
                                          "denver_demo_requests.csv")
        stop_time = SimTime.build('1970-01-01T00:12:00')
        stop_condition = self._generate_stop_condition(stop_time)
        _, stepper = DictReaderStepper.build(test_filename, "departure_time", parser=SimTime.build)
        result = tuple(stepper.read_until_stop_condition(stop_condition))
        self.assertEqual(len(result), 20, f"should have found 20 rows with departure time earlier than {stop_time}")
        self.assertEqual(
            SimTime.build(stepper._iterator.history['departure_time']),
            stop_time,
            f"next has time {stop_time}"
        )
        for row in result:
            self.assertLess(
                SimTime.build(row['departure_time']),
                stop_time,
                f"should be less than {stop_time}"
            )
        stepper.close()

    def test_reading_two_consecutive_times(self):
        test_filename = resource_filename("hive.resources.scenarios.denver_downtown.requests",
                                          "denver_demo_requests.csv")
        _, stepper = DictReaderStepper.build(test_filename, "departure_time", parser=SimTime.build)
        stop1 = SimTime.build('1970-01-01T00:12:00')
        stop2 = SimTime.build('1970-01-01T00:14:00')
        result1 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))
        result2 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop2)))
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time [0, {stop1})")
        self.assertEqual(len(result2), 5, f"should have found 5 rows with departure time [{stop1}, {stop2})")
        for row in result1:
            self.assertLess(
                SimTime.build(row['departure_time']),
                stop1,
                f"should be less than {stop1}")
        for row in result2:
            self.assertGreaterEqual(
                SimTime.build(row['departure_time']),
                stop1,
                f"should be gte {stop1}")
            self.assertLess(
                SimTime.build(row['departure_time']),
                stop2,
                f"should be less than {stop2}")
        stepper.close()

    def test_no_agents_after_end_of_file(self):
        test_filename = resource_filename("hive.resources.scenarios.denver_downtown.requests",
                                          "denver_demo_requests.csv")
        _, stepper = DictReaderStepper.build(test_filename, "departure_time", parser=SimTime.build)
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(SimTime.build(9999998))))
        result = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(SimTime.build(9999999))))
        self.assertEqual(len(result), 0, "should find no more agents after end of time")

    def test_no_second_file_reading_on_repeated_value(self):
        test_filename = resource_filename("hive.resources.scenarios.denver_downtown.requests",
                                          "denver_demo_requests.csv")
        _, stepper = DictReaderStepper.build(test_filename, "departure_time", parser=SimTime.build)
        stop = SimTime.build('1970-01-01T00:12:00')
        result1 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop)))
        result2 = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop)))
        self.assertEqual(len(result1), 20, f"should have found 20 rows with departure time earlier than {stop}")
        self.assertEqual(len(result2), 0, f"will not advance file by calling same stop value {stop}")

    def test_correct_management_of_stored_value_after_repeated_value(self):
        test_filename = resource_filename("hive.resources.scenarios.denver_downtown.requests",
                                          "denver_demo_requests.csv")
        _, stepper = DictReaderStepper.build(test_filename, "departure_time", parser=SimTime.build)
        stop1 = SimTime.build('1970-01-01T00:12:00')
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))
        _ = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop1)))

        # show that second stop1 call means we should have done nothing since the first call
        stop2 = SimTime.build('1970-01-01T00:13:00')
        result = tuple(stepper.read_until_stop_condition(self._generate_stop_condition(stop2)))
        self.assertEqual(len(result), 1, f"should have found 20 rows with departure time earlier than {stop2}")
        self.assertEqual(
            SimTime.build(stepper._iterator.history['departure_time']),
            stop2,
            f"next has time {stop2}"
        )
        for row in result:
            self.assertGreaterEqual(
                SimTime.build(row['departure_time']),
                stop1,
                f"should be gte {stop1}"
            )
            self.assertLess(
                SimTime.build(row['departure_time']),
                stop2,
                f"should be less than {stop2}")
