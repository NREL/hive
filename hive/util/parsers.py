from __future__ import annotations

from typing import Union
from datetime import datetime

from hive.util.typealiases import SimTime


def time_parser(value: str) -> Union[IOError, SimTime]:
    try:
        time = int(datetime.fromisoformat(value).timestamp())
    except (ValueError, TypeError):
        try:
            time = int(value)
        except ValueError:
            return IOError(
                "Unable to parse datetime. \
                Make sure the time is either a unix time integer or an ISO 8601 string")
    return time
