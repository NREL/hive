from __future__ import annotations

from enum import Enum


class ChargingSearchType(Enum):
    NEAREST_SHORTEST_QUEUE = 1
    SHORTEST_TIME_TO_CHARGE = 2

    @staticmethod
    def from_string(string: str) -> ChargingSearchType:
        """
        parses an input configuration string as a ChargingSearchType

        :param string: the input string
        :return: a ChargingSearchType or an Error
        :raises: ValueError when the charging search type is unknown
        """
        cleaned = string.lower()
        if cleaned == "nearest_shortest_queue":
            return ChargingSearchType.NEAREST_SHORTEST_QUEUE
        elif cleaned == "shortest_time_to_charge":
            return ChargingSearchType.SHORTEST_TIME_TO_CHARGE
        else:
            valid_names = "{nearest_shortest_queue|shortest_time_to_charge}"
            raise NameError(f"charging search type {string} is not known, must be one of {valid_names}")
