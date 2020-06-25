from __future__ import annotations

from enum import Enum


class ReportType(Enum):
    """
    A strict set of report types
    """
    STATION_STATE = 1
    VEHICLE_STATE = 2
    ADD_REQUEST_EVENT = 3
    PICKUP_REQUEST_EVENT = 4
    CANCEL_REQUEST_EVENT = 5
    INSTRUCTION = 6
    VEHICLE_CHARGE_EVENT = 7
    VEHICLE_MOVE_EVENT = 8

    @classmethod
    def from_string(cls, s: str) -> ReportType:
        values = {
            "station_state": cls.STATION_STATE,
            "vehicle_state": cls.VEHICLE_STATE,
            "add_request_event": cls.ADD_REQUEST_EVENT,
            "pickup_request_event": cls.PICKUP_REQUEST_EVENT,
            "cancel_request_event": cls.CANCEL_REQUEST_EVENT,
            "instruction": cls.INSTRUCTION,
            "vehicle_charge_event": cls.VEHICLE_CHARGE_EVENT,
            "vehicle_move_event": cls.VEHICLE_MOVE_EVENT,
        }
        try:
            return values[s]
        except KeyError:
            raise KeyError(f"{s} not a valid report type.")