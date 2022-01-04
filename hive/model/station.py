from __future__ import annotations

from distutils.util import strtobool
import functools as ft
from typing import NamedTuple, Dict, Optional

import h3
import immutables
import logging

from hive.model.energy import EnergyType
from hive.model.energy.charger import Charger
from hive.model.membership import Membership
from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.util import DictOps
from hive.util.exception import SimulationStateError
from hive.util.typealiases import *
from hive.util.units import Currency

log = logging.getLogger(__name__)


class Station(NamedTuple):
    """
    A station that vehicles can use to refuel


    :param id: The unique id of the station.
    :type id: :py:obj:`StationId`

    :param geoid: The location of the station.
    :type geoid: :py:obj:`Geoid`

    :param total_chargers: A map of the charger_id types and quanitites for this station.
    :type total_chargers: :py:obj:`Dict[Charger, int]`

    :param available_chargers: Identifies how many plugs for each charger_id type are unoccupied.
    :type available_chargers: :py:obj:`Dict[Charger, int]`

    :param on_shift_access_chargers: Lists the charger ids for chargers that can be used while on-shift (in a station charging search)
    :type on_shift_access_chargers: :py:obj`FrozenSet[ChargerId]`

    :param charger_prices_per_kwh: the cost to use chargers at this station
    :type charger_prices_per_kwh: :py:obj`Dict[Charger, Currency]`

    :param enqueued_vehicles: the count of vehicles currently enqueued for each charger_id
    :type enqueued_vehicles: :py:obj`Dict[Charger, int]`

    :param balance: the net income of this station
    :type balance: :py:obj:`Currency`
    """
    id: StationId
    position: EntityPosition
    total_chargers: immutables.Map[ChargerId, int]
    available_chargers: immutables.Map[ChargerId, int]
    on_shift_access_chargers: FrozenSet[ChargerId]
    charger_prices_per_kwh: immutables.Map[ChargerId, Currency]
    enqueued_vehicles: immutables.Map[ChargerId, int] = immutables.Map()
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
            chargers: immutables.Map[Charger, int],
            on_shift_access: FrozenSet[ChargerId],
            membership: Membership = Membership(),
    ):
        prices = ft.reduce(lambda prices_builder, charger: prices_builder.set(charger, 0.0),
                           chargers.keys(), immutables.Map())
        position = road_network.position_from_geoid(geoid)
        return Station(id=id,
                       position=position,
                       total_chargers=chargers,
                       available_chargers=chargers,
                       on_shift_access_chargers=on_shift_access,
                       charger_prices_per_kwh=prices,
                       membership=membership)

    @classmethod
    def from_row(
        cls,
        row: Dict[str, str],
        builder: Dict[StationId, Station],
        road_network: RoadNetwork,
    ) -> Station:
        """
        takes a csv row and turns it into a Station


        :param row: a row as interpreted by csv.DictReader
        :param builder: the (partially-completed) collection of stations. needed in the case
        that there already was a row parsed for this station

        :param road_network: the road network
        :return: a Station, or an error
        """
        if 'station_id' not in row:
            raise IOError("cannot load a station without a 'station_id'")
        elif 'lat' not in row:
            raise IOError("cannot load a station without an 'lat' value")
        elif 'lon' not in row:
            raise IOError("cannot load a station without an 'lon' value")
        elif 'charger_id' not in row:
            raise IOError("cannot load a station without a 'charger_id' value")
        elif 'charger_count' not in row:
            raise IOError("cannot load a station without a 'charger_count' value")
        elif 'on_shift_access' not in row:
            raise IOError("cannot load a station without an 'on_shift_access' value")
        else:
            station_id = row['station_id']
            try:
                lat, lon = float(row['lat']), float(row['lon'])
                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                charger_id: ChargerId = row['charger_id']
                charger_count = int(float(row['charger_count']))
                on_shift_access = bool(strtobool(row['on_shift_access'].lower()))

                if charger_id is None:
                    raise IOError(
                        f"invalid charger_id type {row['charger_id']} for station {station_id}")
                elif station_id not in builder:
                    # create this station

                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        road_network=road_network,
                        chargers=immutables.Map({charger_id: charger_count}),
                        on_shift_access=frozenset([charger_id]) if on_shift_access else frozenset())
                elif charger_id in builder[station_id].total_chargers:
                    # combine counts from multiple rows which refer to this charger_id
                    charger_already_loaded = builder[station_id].total_chargers[charger_id]

                    # notice we 're-build' the station here. this re-runs the 'price builder' for what
                    # may include a different set of chargers. but, that's not the case here. we could
                    # probably instead use builder[station_id]._replace() instead?
                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        road_network=road_network,
                        chargers=immutables.Map(
                            {charger_id: charger_count + charger_already_loaded}),
                        on_shift_access=builder[station_id].on_shift_access_chargers)
                else:
                    # update this station
                    prev_station = builder[station_id]
                    charger_already_loaded = prev_station.total_chargers
                    updated_chargers = DictOps.add_to_dict(charger_already_loaded, charger_id,
                                                           charger_count)
                    updated_on_shift_access_chargers = prev_station.on_shift_access_chargers.union(
                        [charger_id]) if on_shift_access else prev_station.on_shift_access_chargers

                    return Station.build(id=station_id,
                                         geoid=geoid,
                                         road_network=road_network,
                                         chargers=updated_chargers,
                                         on_shift_access=updated_on_shift_access_chargers)

            except ValueError as v:
                raise IOError(
                    f"unable to parse station {station_id} from row due to invalid value(s): {row}"
                ) from v

    def has_available_charger(self, charger_id: ChargerId) -> bool:
        """
        Indicates if a station has an available charge of type `charger_id`

        :param charger_id: charger_id type to be queried.
        :return: Boolean
        """
        return charger_id in self.total_chargers and self.available_chargers[charger_id] > 0

    def has_on_shift_access_charging(self) -> bool:
        """
        Indicates if this station has at least one charger which is listed as available "on-shift"
        (as opposed to off-shift base charging, home charging, etc)

        :return: true if on shift charging is available
        """
        return len(self.on_shift_access_chargers) > 0

    def checkout_charger(self, charger_id: ChargerId) -> Optional[Station]:
        """
        Checks out a charger_id of type `charger_id` and returns an updated station if there are any available


        :param charger_id: the charger_id type to be checked out
        :return: Updated station or None if no chargers available/ if vehicle is not a member
        """

        if self.has_available_charger(charger_id):
            previous_charger_count = self.available_chargers.get(charger_id)
            updated_avail_chargers = self.available_chargers.set(charger_id,
                                                                 previous_charger_count - 1)
            return self._replace(available_chargers=updated_avail_chargers)
        else:
            return None

    def return_charger(self,
                       charger_id: ChargerId) -> Tuple[Optional[Exception], Optional[Station]]:
        """
        Returns a charger_id of type `charger_id` to the station.
        Raises exception if available chargers exceeds total chargers


        :param charger_id: Charger to be returned
        :return: The updated station with returned charger_id
        """
        if charger_id in self.available_chargers:
            previous_charger_count = self.available_chargers.get(charger_id)
            total_chargers = self.total_chargers.get(charger_id)
            if not total_chargers:
                return SimulationStateError(
                    f"Station {self.id} has no chargers of type {charger_id}"), None
            elif previous_charger_count > total_chargers:
                return SimulationStateError(
                    f"station {self.id} already has max ({total_chargers}) {charger_id} chargers"
                ), None
            updated_avail_chargers = self.available_chargers.set(charger_id,
                                                                 previous_charger_count + 1)
            return None, self._replace(available_chargers=updated_avail_chargers)
        else:
            return None, self

    def update_prices(self, new_prices: immutables.Map[ChargerId, Currency]) -> Station:
        return self._replace(
            charger_prices_per_kwh=DictOps.merge_dicts(self.charger_prices_per_kwh, new_prices))

    def receive_payment(self, currency_received: Currency) -> Station:
        """
        pay for charging costs

        :param currency_received: the currency received for a charge event
        :return: the updated Station
        """
        return self._replace(balance=self.balance + currency_received)

    def enqueue_for_charger(self, charger_id: ChargerId) -> Optional[Station]:
        """
        increment the count of vehicles enqueued for a specific charger_id type - no limit

        :param charger_id: the charger_id type
        :return: the updated Station
        """
        updated_enqueued_count = self.enqueued_vehicles.get(charger_id, 0) + 1
        updated_enqueued_vehicles = self.enqueued_vehicles.set(charger_id, updated_enqueued_count)
        return self._replace(enqueued_vehicles=updated_enqueued_vehicles)

    def dequeue_for_charger(self, charger_id: ChargerId) -> Station:
        """
        decrement the count of vehicles enqueued for a specific charger_id type - min zero

        :param charger_id: the charger_id type
        :param membership: the membership of the vehicle that want's to deque the charger
        :return: the updated Station
        """
        enqueued_count = self.enqueued_vehicles.get(charger_id, 0)
        if not enqueued_count:
            return self
        else:
            updated_enqueued_count = max(0, enqueued_count - 1)
            if updated_enqueued_count == 0:
                updated_enqueued_vehicles = self.enqueued_vehicles.delete(charger_id)
                return self._replace(enqueued_vehicles=updated_enqueued_vehicles)
            else:
                updated_enqueued_vehicles = self.enqueued_vehicles.set(
                    charger_id, updated_enqueued_count)
                return self._replace(enqueued_vehicles=updated_enqueued_vehicles)

    def enqueued_vehicle_count_for_charger(self, charger_id: ChargerId) -> int:
        """
        gets the current count of vehicles enqueued for a specific charger_id at this station

        :param charger_id: the charger_id type
        :return: the count of vehicles enqueued
        """
        return self.enqueued_vehicles.get(charger_id, 0)

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
