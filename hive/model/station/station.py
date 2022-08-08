from __future__ import annotations

from distutils.util import strtobool
import functools as ft
from sre_parse import State
from typing import NamedTuple, Dict, Optional

import h3
import immutables
import logging

from hive.runner.environment import Environment
from hive.model.station.charger_state import ChargerState
from hive.model.energy import EnergyType
from hive.model.energy.charger import Charger
from hive.model.membership import Membership
from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.station.station_ops import station_state_update, station_state_updates
from hive.util.error_or_result import ErrorOr
from hive.util.typealiases import *
from hive.util.units import Currency
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
    def build(cls,
              id: StationId,
              geoid: GeoId,
              road_network: RoadNetwork,
              chargers: immutables.Map[Charger, int],
              on_shift_access: FrozenSet[ChargerId],
              membership: Membership = Membership(),
              ):
        
        # TODO
        # problems with this
        # - mock_station code (and other code) can't call Station.build with a list of
        #   chargers and the count of charger plugs
        # - can't instantiate a station without chargers
        # - if we make it a map from ChargerId to int, we need to pass in the environment
        #   so we can instantiate the Charger here.

        charger_state = ChargerState.build(charger, charger_count)
        position = road_network.position_from_geoid(geoid)
        if position is None:
            raise Exception(f"attempting to build station {id} with invalid position")
        else:
            return Station(
                id=id,
                position=position,
                state=immutables.Map({ charger.id: charger_state }),
                on_shift_access_chargers=on_shift_access,
                membership=membership
            )

    def add_charger(self,
               charger: Charger,
               charger_count: int = 1):
        """
        adds another charger type to this station along with a count of that charger

        :param charger: the charger to add
        :param charger_count: number of plugs to add, defaults to 1
        :return: the updated Station
        """
        # add this charger to the existing station
        charger_state = ChargerState.build(charger, charger_count)
        updated_station_state = self.state.update({charger.id: charger_state})
        updated_on_shift = self.on_shift_access_chargers.union([charger.id])
        updated_station = self._replace(
            state=updated_station_state,
            on_shift_access_chargers=updated_on_shift
        )
        return updated_station

    @classmethod
    def from_row(cls, row: Dict[str, str],
                 builder: Dict[StationId, Station],
                 road_network: RoadNetwork,
                 env: Environment
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
            'station_id',
            'lat',
            'lon',
            'charger_id',
            'charger_count',
            'on_shift_access'
        ]
        validate_fields(row, _EXPECTED_FIELDS)
        
        # decode row string inputs
        station_id = row['station_id']
        try:
            lat, lon = float(row['lat']), float(row['lon'])
            geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
            charger_id: ChargerId = row['charger_id']
            charger = env.chargers.get(charger_id)
            charger_count = int(float(row['charger_count']))
            on_shift_access = bool(strtobool(row['on_shift_access'].lower()))
        except ValueError as v:
            raise IOError(f"unable to parse station {station_id} from row due to invalid value(s): {row}") from v
        
        # handle erroneous input state
        if charger_id is None:
            raise IOError(f"invalid charger_id type {row['charger_id']} for station {station_id}")
        elif charger is None:
            found = ",".join(env.chargers.keys())
            raise IOError(f"charger with id {charger_id} was not provided, found {{{found}}}")
        elif station_id in builder and charger_id in builder[station_id].state.keys():
            msg = (
                f"station id {station_id} has more than one row that references "
                f"charger id {charger_id}"
            )
            raise IOError(msg)

        # add this station to the simulation. this can happen one of two ways:
        # 1. the provided station id has not yet been seen -> create a new station
        # 2. the provided station id has already been seen -> append to existing
        elif station_id not in builder:
            # create this station
            return Station.build(
                id=station_id,
                geoid=geoid,
                road_network=road_network,
                charger=charger,
                charger_count=charger_count,
                on_shift_access=frozenset([charger_id]) if on_shift_access else frozenset()
            )
        else:
            # add this charger to the existing station
            prev_station = builder[station_id]
            updated_station = prev_station.add_charger(charger_id, charger, charger_count)
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

        return station_state_update(self, charger_id, _checkout)

    def return_charger(self, charger_id: ChargerId) -> ErrorOr[Station]:
        """
        Returns a charger_id of type `charger_id` to the station.
        Raises exception if available chargers exceeds total chargers


        :param charger_id: Charger to be returned
        :return: The updated station with returned charger_id
        """
        def _return(cs: ChargerState):
            return cs.increment_available_chargers()

        return station_state_update(
            station=self, 
            charger_id=charger_id, 
            op=lambda cs: cs.increment_available_chargers()
        )

    def update_prices(self, new_prices: immutables.Map[ChargerId, Currency]) -> ErrorOr[Station]:
        
        def _update(cs: ChargerState, price: Currency) -> ErrorOr[ChargerState]:
            return None, cs._replace(price_per_kwh=price)

        return station_state_updates(
            station=self,
            it=new_prices.items(),
            op=_update
        )

    def receive_payment(self, currency_received: Currency) -> Station:
        """
        pay for charging costs

        :param currency_received: the currency received for a charge event
        :return: the updated Station
        """
        return self._replace(balance=self.balance + currency_received)

    def enqueue_for_charger(self, charger_id: ChargerId) -> Station:
        """
        increment the count of vehicles enqueued for a specific charger_id type - no limit

        :param charger_id: the charger_id type
        :return: the updated Station
        """
        def _enqueue(cs: ChargerState) -> ErrorOr[ChargerState]:
            return None, cs.increment_enqueued_vehicles()

        _, updated = station_state_update(
            station=self, 
            charger_id=charger_id, 
            op=_enqueue
        )
        return updated

    def dequeue_for_charger(self, charger_id: ChargerId) -> ErrorOr[Station]:
        """
        decrement the count of vehicles enqueued for a specific charger_id type - min zero

        :param charger_id: the charger_id type
        :param membership: the membership of the vehicle that want's to deque the charger
        :return: the updated Station
        """

        def _dequeue(cs: ChargerState) -> ErrorOr[ChargerState]:
            return cs.decrement_enqueued_vehicles()

        return station_state_update(
            station=self, 
            charger_id=charger_id, 
            op=_dequeue
        )

    def enqueued_vehicle_count_for_charger(self, charger_id: ChargerId) -> Optional[int]:
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
