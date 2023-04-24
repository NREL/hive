import functools as ft
from dataclasses import replace
from typing import Iterable, Optional, TypeVar, Callable, TYPE_CHECKING

from nrel.hive.util.error_or_result import ErrorOr
from nrel.hive.util.typealiases import *

if TYPE_CHECKING:
    from nrel.hive.model.station.charger_state import ChargerState
    from nrel.hive.model.station.station import Station


_EXPECTED_FIELDS = [
    "station_id",
    "lat",
    "lon",
    "charger_id",
    "charger_count",
    "on_shift_access",
]


def station_state_update(
    station: "Station",
    charger_id: ChargerId,
    op: Callable[["ChargerState"], ErrorOr["ChargerState"]],
) -> ErrorOr["Station"]:
    """
    helper function for code where we want to perform an operation on a
    ChargerState and if it does not fail, update the Station with the state
    change.

    :param station: station to update
    :param charger_id: charger id for charger state to update
    :param op: a function to update a ChargerState, which can fail with an error,
               or return an updated ChargerState to replace the state in the Station
    :return: the updated Station or an error
    """
    charger_state = station.state.get(charger_id)
    if charger_state is None:
        # the provided charger type isn't found at this station
        return None, station
    else:
        # apply the operation to this charger state
        err, updated = op(charger_state)
        if err is not None:
            return err, None
        elif updated is None:
            return Exception("got no error and no station"), None
        else:
            updated_s = station.state.set(charger_id, updated)
            result = replace(station, state=updated_s)
            return None, result


def station_state_optional_update(
    station: "Station",
    charger_id: ChargerId,
    op: Callable[["ChargerState"], ErrorOr[Optional["ChargerState"]]],
) -> ErrorOr[Optional["Station"]]:
    """
    helper function for code where we want to perform an operation on a
    ChargerState and if it does not fail, update the Station with the state
    change.

    :param station: station to update
    :param charger_id: charger id for charger state to update
    :param op: a function to update a ChargerState, which can fail with an error,
               or return an updated ChargerState to replace the state in the Station
    :return: the updated Station or an error
    """
    charger_state = station.state.get(charger_id)
    if charger_state is None:
        # the provided charger type isn't found at this station
        return None, station
    else:
        # apply the operation to this charger state
        err, updated = op(charger_state)
        if err is not None:
            return err, None
        elif updated is None:
            # noop
            return None, None
        else:
            updated_s = station.state.set(charger_id, updated)
            result = replace(station, state=updated_s)
            return None, result


T = TypeVar("T")


def station_state_updates(
    station: "Station",
    it: Iterable[Tuple[ChargerId, T]],
    op: Callable[["ChargerState", T], ErrorOr["ChargerState"]],
) -> ErrorOr["Station"]:
    """
    runs a batch update on a station's charger states

    :param station: station to update
    :param it: iterable of ChargerIds and a generic update value
    :param op: operation that applies an update to a ChargerState that
               has access to an instance of T that has a matching ChargerId
    :return: the update result to a station or an error
    """

    def _update(acc, update_tuple):
        err, station = acc
        if err is not None:
            return acc
        else:
            charger_id, t = update_tuple
            return station_state_optional_update(station, charger_id, lambda cs: op(cs, t))

    initial = None, station
    result = ft.reduce(_update, it, initial)
    return result
