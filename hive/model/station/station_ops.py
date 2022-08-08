from typing import Iterable, Optional, TypeVar, Callable, TYPE_CHECKING
from hive.util.error_or_result import ErrorOr
from hive.util.typealiases import *
from hive.util.exception import SimulationStateError

import functools as ft

# if TYPE_CHECKING:
#     from hive.model.station.charger_state import ChargerState
#     from hive.model.station.station import Station


_EXPECTED_FIELDS = [
    'station_id',
    'lat',
    'lon',
    'charger_id',
    'charger_count',
    'on_shift_access'
]

def station_state_update(
    station: 'Station',
    charger_id: ChargerId,
    op: Callable[['ChargerState'], ErrorOr[Optional['ChargerState']]]
    ) -> ErrorOr['Station']:
    """
    helper function for code where we want to perform an operation on a 
    ChargerState and if it does not fail, update the Station with the state
    change.

    :param station: station to update
    :param charger_id: charger id for charger state to update
    :param op: a function to update a ChargerState, which can fail with an error,
               return None which will cancel the update, or, return an updated
               ChargerState to replace the state in the Station
    :return: the updated Station or an error
    """
    charger_state = station.state.get(charger_id)
    err, updated = op(charger_state) if charger_state is not None else None
    if charger_state is None:
        err = SimulationStateError(f"no charger state found for charger id {charger_id}")
        return err, None
    elif err is not None:
        return err, None
    elif updated is None:
        return None, None
    else:
        updated_s = station.state.set(charger_id, updated)
        result = station._replace(state=updated_s)
        return None, result

T = TypeVar("T")

def station_state_updates(
    station: 'Station',
    it: Iterable[Tuple[ChargerId, T]],
    op: Callable[['ChargerState', T], ErrorOr[Optional['ChargerState']]]
    ) -> ErrorOr['Station']:
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
            return station_state_update(
                station, 
                charger_id, 
                lambda cs: op(cs, t)
            )
    
    initial = None, station
    result = ft.reduce(_update, it, initial)
    return result
