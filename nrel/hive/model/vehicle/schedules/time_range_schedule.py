import functools as ft
from csv import DictReader
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from immutables import Map

from nrel.hive.model.vehicle.schedules.schedule import ScheduleFunction
from nrel.hive.util.time_helpers import read_time_string, time_in_range
from nrel.hive.util.typealiases import VehicleId, ScheduleId


def time_range_schedules_from_file(
    file: str,
) -> Map[ScheduleId, ScheduleFunction]:
    """
    given a CSV file of time ranges by ScheduleId, construct a time range schedule table

    :param file: the CSV file
    :return: the schedules
    """
    file_path = Path(file)
    with file_path.open("r") as f:
        reader = DictReader(f)
        initial = Map[ScheduleId, ScheduleFunction]()
        result = ft.reduce(read_time_range_row, reader, initial)

    return result


def time_range_schedules_from_string(
    string: str,
) -> Map[ScheduleId, ScheduleFunction]:
    """
    given a string in CSV format, construct a time range schedule table

    :param string: the CSV file string
    :return: the schedules
    """
    reader = DictReader(string.split())
    initial = Map[ScheduleId, ScheduleFunction]()
    result = ft.reduce(read_time_range_row, reader, initial)

    return result


def read_time_range_row(acc: Map[ScheduleId, ScheduleFunction], row: Dict):
    """
    reads a row of a time range CSV file, adding the associated range as a
    schedule function to the accumulator


    :param acc: the collection we are adding this row to

    :param row: the DictReader row of the time range file
    :return: the updated accumulator
    """
    schedule_id: Optional[ScheduleId] = row.get("schedule_id")
    if schedule_id is None:
        raise KeyError("must provide schedule id")
    start_time_string = row.get("start_time")
    if not start_time_string:
        raise KeyError("time range file missing start_time column or entry missing")
    end_time_string = row.get("end_time")
    if not end_time_string:
        raise KeyError("time range file missing end_time column or entry missing")
    start_time = read_time_string(start_time_string)
    end_time = read_time_string(end_time_string)

    def _schedule_fn(sim, vehicle_id: VehicleId) -> bool:
        sim_time = datetime.utcfromtimestamp(sim.sim_time).time()
        within_scheduled_time = time_in_range(start_time, end_time, sim_time)
        return within_scheduled_time

    updated_schedules = acc.set(schedule_id, _schedule_fn)
    return updated_schedules
