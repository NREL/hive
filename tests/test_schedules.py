from unittest import TestCase

from hive.model.vehicle.schedules.time_range_schedule import time_range_schedules_from_string
from hive.resources.mock_lobster import *


class TestSchedules(TestCase):

    def test_time_range_schedule(self):
        schedules_input = """schedule_id,start_time,end_time
                             first,"09:00:00","17:00:00"
                             second,"17:00:00","01:00:00"
                             third,"00:00:00","08:00:00"
                             """
        time_range_schedules = time_range_schedules_from_string(schedules_input)

        eight_am = 3600 * 8
        ten_am = 3600 * 10
        midnight = 0
        eleven_fifty_nine_fifty_nine = 86399
        # not_a_time = 87000  # todo: maybe worth adding a test for times outside of the day range?

        first_shift_schedule_fn: ScheduleFunction = time_range_schedules.get("first")
        second_shift_schedule_fn: ScheduleFunction = time_range_schedules.get("second")
        third_shift_schedule_fn: ScheduleFunction = time_range_schedules.get("third")
        unused = DefaultIds.mock_vehicle_id()

        self.assertFalse(first_shift_schedule_fn(mock_sim(sim_time=eight_am), unused))
        self.assertTrue(first_shift_schedule_fn(mock_sim(sim_time=ten_am), unused))
        self.assertFalse(first_shift_schedule_fn(mock_sim(sim_time=midnight), unused))
        self.assertFalse(first_shift_schedule_fn(mock_sim(sim_time=eleven_fifty_nine_fifty_nine), unused))
        # self.assertFalse(first_shift_schedule_fn(mock_sim(sim_time=not_a_time), unused))

        self.assertFalse(second_shift_schedule_fn(mock_sim(sim_time=eight_am), unused))
        self.assertFalse(second_shift_schedule_fn(mock_sim(sim_time=ten_am), unused))
        self.assertTrue(second_shift_schedule_fn(mock_sim(sim_time=midnight), unused))
        self.assertTrue(second_shift_schedule_fn(mock_sim(sim_time=eleven_fifty_nine_fifty_nine), unused))
        # self.assertFalse(second_shift_schedule_fn(mock_sim(sim_time=not_a_time), unused))

        self.assertFalse(third_shift_schedule_fn(mock_sim(sim_time=eight_am), unused))
        self.assertFalse(third_shift_schedule_fn(mock_sim(sim_time=ten_am), unused))
        self.assertTrue(third_shift_schedule_fn(mock_sim(sim_time=midnight), unused))
        self.assertFalse(third_shift_schedule_fn(mock_sim(sim_time=eleven_fifty_nine_fifty_nine), unused))
        # self.assertFalse(third_shift_schedule_fn(mock_sim(sim_time=not_a_time), unused))
