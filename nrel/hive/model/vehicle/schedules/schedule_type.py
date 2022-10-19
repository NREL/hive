from __future__ import annotations

from enum import Enum


class ScheduleType(Enum):
    TIME_RANGE = 0

    @staticmethod
    def from_string(string: str) -> ScheduleType:
        """
        parses an input configuration string as a ChargingSearchType

        :param string: the input string
        :return: a ChargingSearchType or an Error
        :raises: ValueError when the charging search type is unknown
        """
        cleaned = string.lower().strip()
        if cleaned == "time_range":
            return ScheduleType.TIME_RANGE
        else:
            valid_names_list = list(ScheduleType)
            valid_names = ", ".join(list(map(lambda x: x.name, valid_names_list)))
            raise NameError(
                f"schedule type '{string}' is not known, must be one of {{{valid_names}}}"
            )
