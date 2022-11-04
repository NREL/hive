from datetime import datetime, timedelta, date, time


def time_in_range(start, end, x):
    """
    Return true if x is in the range [start, end).
    adapted from https://stackoverflow.com/a/10748024 with end-exclusive matching added
    """
    if start <= end:
        return start <= x < end
    else:
        return start <= x or x < end


def read_time_string(input_string: str) -> time:
    """
    parses a string in HH:MM:SS format into a datetime.time object

    :param input_string: the input string
    :return: the time parsed, or, an error
    """
    return datetime.strptime(input_string, "%H:%M:%S").time()


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
