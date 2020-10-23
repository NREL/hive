from __future__ import annotations

from datetime import datetime
from typing import Union

from hive.util.typealiases import SimTime


def time_parser(value: str) -> Union[IOError, SimTime]:
    try:
        time = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        try:
            time = datetime.fromtimestamp(int(value))
        except (ValueError, TypeError):
            return IOError("Unable to parse datetime. Make sure the time is an ISO 8601 string or an epoch integer")

    if time.tzinfo:
        return NotImplemented("Timezones are not supported in hive. Please remove any timezone info")

    return int(time.timestamp())


