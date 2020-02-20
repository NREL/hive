from __future__ import annotations

from typing import NamedTuple, Dict, Optional
import functools as ft

import immutables
from h3 import h3

from hive.model.energy.charger import Charger
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.link import Link
from hive.util.exception import SimulationStateError
from hive.util.helpers import DictOps
from hive.util.typealiases import *
from hive.util.units import Currency


class Station(NamedTuple):
    """
    A station that vehicles can use to refuel

    :param id: The unique id of the station.
    :type id: :py:obj:`StationId`
    :param geoid: The location of the station.
    :type geoid: :py:obj:`Geoid`
    :param total_chargers: A map of the charger types and quanitites for this station.
    :type total_chargers: :py:obj:`Dict[Charger, int]`
    :param available_chargers: Identifies how many plugs for each charger type are unoccupied.
    :type available_chargers: :py:obj:`Dict[Charger, int]`
    """
    id: StationId
    link: Link
    total_chargers: immutables.Map[Charger, int]
    available_chargers: immutables.Map[Charger, int]
    charger_prices: immutables.Map[Charger, Currency]
    balance: Currency = 0.0

    @property
    def geoid(self) -> GeoId:
        return self.link.start

    @classmethod
    def build(cls,
              id: StationId,
              geoid: GeoId,
              road_network: RoadNetwork,
              chargers: immutables.Map[Charger, int]
              ):
        prices = ft.reduce(
            lambda prices_builder, charger: prices_builder.set(charger, 0.0),
            chargers.keys(),
            immutables.Map()
        )
        link = road_network.link_from_geoid(geoid)
        return Station(id, link, chargers, chargers, prices)

    @classmethod
    def from_row(cls, row: Dict[str, str],
                 builder: Dict[StationId, Station],
                 road_network: RoadNetwork,
                 ) -> Station:
        """
        takes a csv row and turns it into a Station

        :param row: a row as interpreted by csv.DictReader
        :param builder: the (partially-completed) collection of stations. needed in the case
        that there already was a row parsed for this station
        :return: a Station, or an error
        """
        if 'station_id' not in row:
            raise IOError("cannot load a station without a 'station_id'")
        elif 'lat' not in row:
            raise IOError("cannot load a station without an 'lat' value")
        elif 'lon' not in row:
            raise IOError("cannot load a station without an 'lon' value")
        elif 'charger_type' not in row:
            raise IOError("cannot load a station without a 'charger_type' value")
        elif 'charger_count' not in row:
            raise IOError("cannot load a station without a 'charger_count' value")
        else:
            station_id = row['station_id']
            try:
                lat, lon = float(row['lat']), float(row['lon'])
                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                charger_type = Charger.from_string(row['charger_type'])
                charger_count = int(row['charger_count'])

                if charger_type is None:
                    raise IOError(f"invalid charger type {row['charger']} for station {station_id}")
                elif station_id not in builder:
                    # create this station
                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        road_network=road_network,
                        chargers=immutables.Map({charger_type: charger_count})
                    )
                elif charger_type in builder[station_id].total_chargers:
                    # combine counts from multiple rows which refer to this charger_type
                    charger_already_loaded = builder[station_id].total_chargers[charger_type]

                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        road_network=road_network,
                        chargers=immutables.Map({charger_type: charger_count + charger_already_loaded})
                    )
                else:
                    # update this station charger_already_loaded = builder[station_id].total_chargers
                    charger_already_loaded = builder[station_id].total_chargers
                    updated_chargers = DictOps.add_to_dict(charger_already_loaded, charger_type, charger_count)

                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        road_network=road_network,
                        chargers=updated_chargers
                    )

            except ValueError:
                raise IOError(f"unable to parse request {station_id} from row due to invalid value(s): {row}")

    def has_available_charger(self, charger: Charger) -> bool:
        """
        Indicates if a station has an available charge of type `charger`

        :param charger: charger type to be queried.
        :return: Boolean
        """
        return charger in self.total_chargers and self.available_chargers[charger] > 0

    def checkout_charger(self, charger: Charger) -> Optional[Station]:
        """
        Checks out a charger of type `charger` and returns an updated station if there are any available

        :param charger: the charger type to be checked out
        :return: Updated station or None if no chargers available
        """

        if self.has_available_charger(charger):
            previous_charger_count = self.available_chargers.get(charger)
            updated_avail_chargers = self.available_chargers.set(charger, previous_charger_count - 1)
            return self._replace(available_chargers=updated_avail_chargers)
        else:
            return None

    def return_charger(self, charger: Charger) -> Station:
        """
        Returns a charger of type `charger` to the station.
        Raises exception if available chargers exceeds total chargers

        :param charger: Charger to be returned
        :return: The updated station with returned charger
        """
        if charger in self.available_chargers:
            previous_charger_count = self.available_chargers.get(charger)
            if previous_charger_count > self.total_chargers.get(charger):
                raise SimulationStateError("Station already has max chargers of this type")
            updated_avail_chargers = self.available_chargers.set(charger, previous_charger_count + 1)
            return self._replace(available_chargers=updated_avail_chargers)
        else:
            return self

    def update_prices(self, new_prices: immutables.Map[Charger, Currency]) -> Station:
        return self._replace(
            charger_prices=DictOps.merge_dicts(self.charger_prices, new_prices)
        )

    def receive_payment(self, currency_received: Currency) -> Station:
        """
        pay for charging costs
        :param currency_received: the currency received for a charge event
        :return: the updated Station
        """
        return self._replace(balance=self.balance + currency_received)