from __future__ import annotations

from datetime import datetime, time
from typing import Union

from nrel.hive.util.exception import TimeParseError


class SimTime(int):
    ERROR_MSG = (
        "Unable to parse datetime. Make sure the time is an ISO 8601 string or an epoch integer."
    )

    @classmethod
    def build(cls, value: Union[str, int]) -> SimTime:
        if isinstance(value, str):
            try:
                time = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                try:
                    time = datetime.utcfromtimestamp(int(value))
                except (ValueError, TypeError):
                    raise TimeParseError(cls.ERROR_MSG + f" got {value}")
        elif isinstance(value, int):
            try:
                time = datetime.utcfromtimestamp(value)
            except (ValueError, TypeError):
                raise TimeParseError(cls.ERROR_MSG + f" got {value}")
        else:
            raise TimeParseError(cls.ERROR_MSG + f" got {value}")

        if time.tzinfo:
            time = time.replace(tzinfo=None)

        utc_time = (time - datetime(1970, 1, 1)).total_seconds()

        return SimTime(int(utc_time))

    def __new__(cls, value, *args, **kwargs):
        return super(cls, cls).__new__(cls, value)

    def __add__(self, other):
        res = super(SimTime, self).__add__(other)
        return self.__class__(res)

    def __sub__(self, other):
        res = super(SimTime, self).__sub__(other)
        return self.__class__(res)

    def __mul__(self, other):
        res = super(SimTime, self).__mul__(other)
        return self.__class__(res)

    def __repr__(self):
        return self.as_iso_time()

    def __str__(self):
        return self.as_iso_time()

    def as_datetime_time(self) -> time:
        return datetime.utcfromtimestamp(int(self)).time()

    def as_epoch_time(self) -> int:
        return int(self)

    def as_iso_time(self) -> str:
        return datetime.utcfromtimestamp(int(self)).isoformat()
