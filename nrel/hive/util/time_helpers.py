from datetime import time, datetime, date, timedelta
import re


def time_in_range(start, end, x):
    """
    Return true if x is in the range [start, end).
    adapted from https://stackoverflow.com/a/10748024 with end-exclusive matching added
    """
    if start <= end:
        return start <= x < end
    else:
        return start <= x or x < end


def read_time_string(s: str) -> time:
    """
    parses a string in HH:MM:SS format into a datetime.time object

    :param s: the input string
    :return: the time parsed, or, an error
    """
    time_regex = r"(\d|0\d|1\d|2[0123]):([012345]\d):([012345]\d)"
    matches = re.match(time_regex, s.strip())
    if not matches:
        raise ValueError(f"could not parse HH:MM:SS from {s}")
    else:
        try:
            h, m, s = tuple(map(lambda x: int(x), matches.groups()))
            time_value = time(hour=h, minute=m, second=s)
            return time_value
        except Exception as e:
            raise ValueError("unexpected error condition while parsing time from string") from e


def time_diff(start: time, end: time) -> timedelta:
    """
    finds the time delta between two times. result has date line transitions removed.

    :param start: the start time
    :param end: the end time
    :return: the time between the start event and the finish event, in hours/minutes/seconds
    """
    if start == end:
        return timedelta()
    else:
        duration = datetime.combine(date.min, end) - datetime.combine(date.min, start)
        if duration.days == -1:
            # remove the "days" from the time transition
            duration_without_day = duration + timedelta(days=1)
            return duration_without_day
        else:
            return duration
