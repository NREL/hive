from immutables import Map

from nrel.hive.model.vehicle.schedules.schedule import ScheduleFunction
from nrel.hive.model.vehicle.schedules.schedule_type import ScheduleType
from nrel.hive.model.vehicle.schedules.time_range_schedule import time_range_schedules_from_file
from nrel.hive.util.typealiases import ScheduleId

# each is expected to be a one-argument function that takes a file path
_constructors = {ScheduleType.TIME_RANGE: time_range_schedules_from_file}


def build_schedules_table(
    schedule_type: ScheduleType, schedules_file: str
) -> Map[ScheduleId, ScheduleFunction]:
    """
    builds the schedule table based on the provided schedule type and file

    :param schedule_type: the type of schedule to load. different schedule types require
    different programmatic implementations and argument types/structures

    :param schedules_file: the file providing parameters for the schedule type
    :return: a schedule lookup table for the simulation environment
    """

    schedule_fn_constructor = _constructors.get(schedule_type)
    if not schedule_fn_constructor:
        raise KeyError(f"schedule type {schedule_type.name} not implemented")
    else:
        schedules = schedule_fn_constructor(schedules_file)
        return schedules
