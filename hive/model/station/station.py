from __future__ import annotations

from distutils.util import strtobool
import functools as ft
from typing import NamedTuple, Dict, Optional, Union

import h3
import immutables
import logging

from returns.result import ResultE, Success, Failure
from hive.model.energy import charger

from hive.runner.environment import Environment
from hive.model.station.charger_state import ChargerState
from hive.model.energy import EnergyType
from hive.model.energy.charger import Charger
from hive.model.membership import Membership
from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.station.station_ops import (
    station_state_update,
    station_state_optional_update,
    station_state_updates,
)
from hive.util.error_or_result import ErrorOr
from hive.util.typealiases import *
from hive.util.exception import H3Error, SimulationStateError
from hive.util.units import Currency, KwH
from hive.util.validation import validate_fields

log = logging.getLogger(__name__)


class Station(NamedTuple):
    """
    A station that vehicles can use to refuel


    :param id: The unique id of the station.
    :type id: :py:obj:`StationId`

    :param geoid: The location of the station.
    :type geoid: :py:obj:`Geoid`

    :param state: state of the chargers at this station
    :type state: :py:obj`Map[ChargerId, ChargerState]`

    :param on_shift_access_chargers: Lists the charger ids for chargers that can be used while on-shift (in a station charging search)
    :type on_shift_access_chargers: :py:obj`FrozenSet[ChargerId]`

    :param balance: the net income of this station
    :type balance: :py:obj:`Currency`
    """

    id: StationId
    position: EntityPosition
    state: immutables.Map[ChargerId, ChargerState]
    on_shift_access_chargers: FrozenSet[ChargerId]
    balance: Currency = 0.0
    membership: Membership = Membership()

    @property
    def geoid(self) -> GeoId:
        return self.position.geoid

    @classmethod
    def build(
        cls,
        id: StationId,
        geoid: GeoId,
        road_network: RoadNetwork,
        chargers: immutables.Map[ChargerId, int],
        on_shift_access: FrozenSet[ChargerId],
        membership: Membership,
        env: Environment,
    ):

        # TODO
        # problems with this
        # - mock_station code (and other code) can't call Station.build with a list of
        #   chargers and the count of charger plugs
        # - can't instantiate a station without chargers
        # - if we make it a map from ChargerId to int, we need to pass in the environment
        #   so we can instantiate the Charger here.

        def _chargers(acc, charger_data):
            """
            an inner function that attempts to build a charger state for the chargers argument
            which provies charger ids and counts. builds on a Map which may also have an error
            when the provided charger id doesn't exist.
            """
            err, builder = acc
            if err is not None:
                return acc
            else:
                charger_id, charger_count = charger_data
                charger = env.chargers.get(charger_id)
                if charger is None:
                    msg = (
                        f"attempting to create station {id} with charger type {charger_id} "
                        f"but that charger type has not been defined for this scenario"
                    )
                    return TypeError(msg), None
                else:
                    charger_state = ChargerState.build(charger, charger_count)
                    updated_builder = builder.set(charger_id, charger_state)
                    return None, updated_builder

        initial = None, immutables.Map[ChargerId, ChargerState]()
        error, charger_states = ft.reduce(_chargers, chargers.items(), initial)
        if error is not None:
            raise error
        if charger_states is None:
            msg = f"internal error after building station chargers for station {id}"
            raise Exception(msg)

        position = road_network.position_from_geoid(geoid)
        if position is None:
            msg = (
                "could not find a road network position matching the position "
                f"provided for station {id}"
            )
            raise H3Error(msg)
        return Station(
            id=id,
            position=position,
            state=charger_states,
            on_shift_access_chargers=on_shift_access,
            membership=membership,
        )

    def append_chargers(
        self, charger_id: ChargerId, charger_count: int, env: Environment
    ) -> ErrorOr[Station]:
        """
        adds chargers to existing station along with amount of chargers to add.
        this method has "append" semantics: if this charger_id already exists at
        this station, we simply add more charger_counts to it.

        :param charger_id: the type of charger to add
        :param charger_count: number of plugs to add
        :param env: simulation environment
        :return: the updated Station
        """
        cs = self.state.get(charger_id)
        if cs is not None:
            # this charger type is already defined on this station: APPEND
            append_cs = cs.add_chargers(charger_count)
        else:
            # add this charger to the existing station
            charger = env.chargers.get(charger_id)
            if charger is None:
                msg = (
                    f"attempting to create station {id} with charger type {charger_id} "
                    f"but that charger type has not been defined for this scenario"
                )
                return TypeError(msg), None
            append_cs = ChargerState.build(charger, charger_count)

        updated_station_state = self.state.update({charger_id: append_cs})
        updated_on_shift = self.on_shift_access_chargers.union([charger_id])
        updated_station = self._replace(
            state=updated_station_state, on_shift_access_chargers=updated_on_shift
        )
        return None, updated_station

    @classmethod
    def from_row(
        cls,
        row: Dict[str, str],
        builder: Union[immutables.Map[StationId, Station], Dict[StationId, Station]],
        road_network: RoadNetwork,
        env: Environment,
    ) -> Station:
        """
        takes a csv row and turns it into a Station


        :param row: a row as interpreted by csv.DictReader
        :param builder: the (partially-completed) collection of stations. needed in the case
        that there already was a row parsed for this station

        :param road_network: the road network
        :return: a Station, or an error
        """
        _EXPECTED_FIELDS = [
            "station_id",
            "lat",
            "lon",
            "charger_id",
            "charger_count",
            "on_shift_access",
        ]
        validate_fields(row, _EXPECTED_FIELDS)

        # decode row string inputs
        station_id = row["station_id"]
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
            geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
            charger_id: ChargerId = row["charger_id"]
            charger_count = int(float(row["charger_count"]))
            on_shift_access = bool(strtobool(row["on_shift_access"].lower()))
        except ValueError as v:
            raise IOError(
                f"unable to parse station {station_id} from row due to invalid value(s): {row}"
            ) from v

        # add this station to the simulation. this can happen one of two ways:
        # 1. the provided station id has not yet been seen -> create a new station
        # 2. the provided station id has already been seen -> append to existing
        if charger_id is None:
            raise IOError(
                f"invalid charger_id type {row['charger_id']} for station {station_id}"
            )
        elif station_id not in builder:
            # create this station
            return Station.build(
                id=station_id,
                geoid=geoid,
                road_network=road_network,
                chargers=immutables.Map({charger_id: charger_count}),
                on_shift_access=frozenset([charger_id])
                if on_shift_access
                else frozenset(),
                membership=Membership(),
                env=env,
            )
        else:
            # add this charger to the existing station
            prev_station = builder[station_id]
            error, updated_station = prev_station.append_chargers(
                charger_id, charger_count, env
            )
            if error is not None:
                raise error
            return updated_station

    def get_price(self, charger_id: ChargerId) -> Optional[Currency]:
        """
        gets the price for a charger type at this station

        :param charger_id: the charger id to get the price for
        :return: the price if this charger type is at this station
        """
        cs = self.state.get(charger_id)
        price = cs.price_per_kwh if cs is not None else None
        return price

    def get_charger_instance(self, charger_id: ChargerId) -> ErrorOr[Charger]:
        """
        gets a Charger with a specific charger id from this station. this
        returns a Charger from the Station.state collection, which allows for
        modifications to the charging rate local to this station.

        :param charger_id: id of the charger
        :return: the Charger instance, or, an error
        """
        cs = self.state.get(charger_id)
        if cs is None:
            msg = (
                f"attempting to get charger {charger_id} at station {self.id} "
                f"but this station does not have that kind of charger"
            )
            return SimulationStateError(msg), None
        else:
            return None, cs.charger

    def get_available_chargers(self, charger_id: ChargerId) -> Optional[int]:
        """
        gets the number of available chargers for a charger type at this station

        :param charger_id: the charger id to get the price for
        :return: the number of available chargers of this charger type at this station
        """
        cs = self.state.get(charger_id)
        chargers = cs.available_chargers if cs is not None else None
        return chargers

    def get_total_chargers(self, charger_id: ChargerId) -> Optional[int]:
        """
        gets the number of installed charge plugs for a charger type at this station
        which is the total, not the currently available set

        :param charger_id: the charger id to get the price for
        :return: the number of chargers of this charger type at this station
        """
        cs = self.state.get(charger_id)
        chargers = cs.total_chargers if cs is not None else None
        return chargers

    def has_available_charger(self, charger_id: ChargerId) -> bool:
        """
        Indicates if a station has an available charge of type `charger_id`

        :param charger_id: charger_id type to be queried.
        :return: Boolean
        """
        charger_state = self.state.get(charger_id)
        if charger_state is None:
            return False
        else:
            return charger_state.has_available_charger()

    def has_on_shift_access_charging(self) -> bool:
        """
        Indicates if this station has at least one charger which is listed as available "on-shift"
        (as opposed to off-shift base charging, home charging, etc)

        :return: true if on shift charging is available
        """
        return len(self.on_shift_access_chargers) > 0

    def checkout_charger(self, charger_id: ChargerId) -> ErrorOr[Optional[Station]]:
        """
        Checks out a charger_id of type `charger_id` and returns an updated station if there are any available


        :param charger_id: the charger_id type to be checked out
        :return: Updated station or None if no chargers available/ if vehicle is not a member
        """

        def _checkout(cs: ChargerState):
            if not cs.has_available_charger():
                return None, None
            else:
                return cs.decrement_available_chargers()

        return station_state_optional_update(self, charger_id, _checkout)

    def return_charger(self, charger_id: ChargerId) -> ErrorOr[Station]:
        """
        Returns a charger_id of type `charger_id` to the station.
        Raises exception if available chargers exceeds total chargers


        :param charger_id: Charger to be returned
        :return: The updated station with returned charger_id
        """

        def _return(cs: ChargerState) -> ErrorOr[ChargerState]:
            return cs.increment_available_chargers()

        return station_state_update(station=self, charger_id=charger_id, op=_return)

    def set_charger_rate(self, charger_id: ChargerId, rate: KwH) -> ResultE[Station]:
        """
        Set the rate for a charger.

        :param charger_id: The charger to update.
        :param rate: The rate to update to (in kwh)

        :return: The updated station or an error
        """
        charger_state = self.state.get(charger_id)
        if charger_state is None:
            err = SimulationStateError(
                f"Charger id {charger_id} does not exist at station {self.id}"
            )
            return Failure(err)

        new_charger_state_or_err = charger_state.set_charge_rate(rate)
        if isinstance(new_charger_state_or_err, Failure):
            return new_charger_state_or_err
        else:
            new_charger_state = new_charger_state_or_err.unwrap()
            new_state = self.state.set(charger_id, new_charger_state)
            new_station = self._replace(state=new_state)
            return Success(new_station)

    def scale_charger_rate(
        self, charger_id: ChargerId, scale: float
    ) -> ResultE[Station]:
        """
        Scale the charging rate for a charger.

        :param charger_id: The charger to update.
        :param scale: The scale factor to use. Must be between [0, 1]

        :return: The updated station or an error
        """
        charger_state = self.state.get(charger_id)
        if charger_state is None:
            err = SimulationStateError(
                f"Charger id {charger_id} does not exist at station {self.id}"
            )
            return Failure(err)

        new_charger_state_or_err = charger_state.scale_charge_rate(scale)
        if isinstance(new_charger_state_or_err, Failure):
            return new_charger_state_or_err
        else:
            new_charger_state = new_charger_state_or_err.unwrap()
            new_state = self.state.set(charger_id, new_charger_state)
            new_station = self._replace(state=new_state)
            return Success(new_station)

    def update_prices(
        self, new_prices: immutables.Map[ChargerId, Currency]
    ) -> ErrorOr[Station]:
        def _update(cs: ChargerState, price: Currency) -> ErrorOr[ChargerState]:
            return None, cs._replace(price_per_kwh=price)

        return station_state_updates(station=self, it=new_prices.items(), op=_update)

    def receive_payment(self, currency_received: Currency) -> Station:
        """
        pay for charging costs

        :param currency_received: the currency received for a charge event
        :return: the updated Station
        """
        return self._replace(balance=self.balance + currency_received)

    def enqueue_for_charger(self, charger_id: ChargerId) -> ErrorOr[Station]:
        """
        increment the count of vehicles enqueued for a specific charger_id type - no limit

        :param charger_id: the charger_id type
        :return: the updated Station
        """

        def _enqueue(cs: ChargerState) -> ErrorOr[ChargerState]:
            return None, cs.increment_enqueued_vehicles()

        return station_state_update(station=self, charger_id=charger_id, op=_enqueue)

    def dequeue_for_charger(self, charger_id: ChargerId) -> ErrorOr[Station]:
        """
        decrement the count of vehicles enqueued for a specific charger_id type - min zero

        :param charger_id: the charger_id type
        :param membership: the membership of the vehicle that want's to deque the charger
        :return: the updated Station
        """

        def _dequeue(cs: ChargerState) -> ErrorOr[ChargerState]:
            return cs.decrement_enqueued_vehicles()

        return station_state_update(station=self, charger_id=charger_id, op=_dequeue)

    def enqueued_vehicle_count_for_charger(
        self, charger_id: ChargerId
    ) -> Optional[int]:
        """
        gets the current count of vehicles enqueued for a specific charger_id at this station

        :param charger_id: the charger_id type
        :return: the count of vehicles enqueued
        """
        state = self.state.get(charger_id)
        if state is None:
            return None
        else:
            return state.enqueued_vehicles

    def set_membership(self, member_ids: Tuple[str, ...]) -> Station:
        """
        sets the membership(s) of the station

        :param member_ids: a Tuple containing updated membership(s) of the station
        :return:
        """
        return self._replace(membership=Membership.from_tuple(member_ids))

    def add_membership(self, membership_id: MembershipId) -> Station:
        """
        adds the membership to the station

        :param membership_id: a membership for the station
        :return: updated station
        """
        updated_membership = self.membership.add_membership(membership_id)
        return self._replace(membership=updated_membership)
