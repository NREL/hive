from __future__ import annotations

from datetime import datetime
from typing import Union

from hive.model.sim_time import SimTime


def time_parser(value: Union[str, int]) -> Union[IOError, SimTime]:
    if isinstance(value, str):
        try:
            time = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            try:
                time = datetime.utcfromtimestamp(int(value))
            except (ValueError, TypeError):
                return IOError("Unable to parse datetime. Make sure the time is an ISO 8601 string or an epoch integer")
    elif isinstance(value, int):
        try:
            time = datetime.utcfromtimestamp(value)
        except (ValueError, TypeError):
            return IOError("Unable to parse datetime. Make sure the time is an ISO 8601 string or an epoch integer")
    else:
        return IOError("Unable to parse datetime. Make sure the time is an ISO 8601 string or an epoch integer")

    if time.tzinfo:
        return NotImplemented("Timezones are not supported in hive. Please remove any timezone info")

    utc_time = (time - datetime(1970, 1, 1)).total_seconds()

    return SimTime(int(utc_time))


