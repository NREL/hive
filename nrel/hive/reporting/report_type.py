from __future__ import annotations

from enum import Enum


class ReportType(Enum):
    """
    A strict set of report types
    """

    STATION_STATE = 1
    VEHICLE_STATE = 2
    DRIVER_STATE = 3
    ADD_REQUEST_EVENT = 4
    PICKUP_REQUEST_EVENT = 5
    DROPOFF_REQUEST_EVENT = 6
    CANCEL_REQUEST_EVENT = 7
    INSTRUCTION = 8
    VEHICLE_CHARGE_EVENT = 9
    VEHICLE_MOVE_EVENT = 10
    STATION_LOAD_EVENT = 11
    REFUEL_SEARCH_EVENT = 12
    DRIVER_SCHEDULE_EVENT = 13

    @classmethod
    def from_string(cls, s: str) -> ReportType:
        values = {
            "station_state": cls.STATION_STATE,
            "vehicle_state": cls.VEHICLE_STATE,
            "driver_state": cls.DRIVER_STATE,
            "add_request_event": cls.ADD_REQUEST_EVENT,
            "pickup_request_event": cls.PICKUP_REQUEST_EVENT,
            "dropoff_request_event": cls.DROPOFF_REQUEST_EVENT,
            "cancel_request_event": cls.CANCEL_REQUEST_EVENT,
            "instruction": cls.INSTRUCTION,
            "vehicle_charge_event": cls.VEHICLE_CHARGE_EVENT,
            "vehicle_move_event": cls.VEHICLE_MOVE_EVENT,
            "station_load_event": cls.STATION_LOAD_EVENT,
            "refuel_search_event": cls.REFUEL_SEARCH_EVENT,
            "driver_schedule_event": cls.DRIVER_SCHEDULE_EVENT,
        }
        try:
            return values[s]
        except KeyError:
            raise KeyError(f"{s} not a valid report type.")
