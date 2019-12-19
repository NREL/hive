from __future__ import annotations

from typing import NamedTuple, Dict, Optional, Union

from hive.model.energy.charger import Charger
from hive.util.exception import SimulationStateError
from hive.util.helpers import DictOps
from hive.util.typealiases import *

from h3 import h3


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
    geoid: GeoId
    total_chargers: Dict[Charger, int]
    available_chargers: Dict[Charger, int]

    @classmethod
    def build(cls,
              id: StationId,
              geoid: GeoId,
              chargers: Dict[Charger, int]
              ):
        return Station(id, geoid, chargers, chargers)

    @classmethod
    def from_row(cls, row: Dict[str, str],
                 builder: Dict[StationId, Station],
                 sim_h3_resolution: int) -> Union[IOError, Station]:
        """
        takes a csv row and turns it into a Station

        :param row: a row as interpreted by csv.DictReader
        :param builder: the (partially-completed) collection of stations. needed in the case
        that there already was a row parsed for this station
        :param sim_h3_resolution: the h3 resolution that events are experienced at
        :return: a Station, or an error
        """
        if 'station_id' not in row:
            return IOError("cannot load a station without a 'station_id'")
        elif 'lat' not in row:
            return IOError("cannot load a station without an 'lat' value")
        elif 'lon' not in row:
            return IOError("cannot load a station without an 'lon' value")
        elif 'charger_type' not in row:
            return IOError("cannot load a station without a 'charger_type' value")
        elif 'charger_count' not in row:
            return IOError("cannot load a station without a 'charger_count' value")
        else:
            station_id = row['station_id']
            try:
                lat, lon = float(row['lat']), float(row['lon'])
                geoid = h3.geo_to_h3(lat, lon, sim_h3_resolution)
                charger_type = Charger.from_string(row['charger_type'])
                charger_count = int(row['charger_count'])

                if charger_type is None:
                    return IOError(f"invalid charger type {row['charger']} for station {station_id}")
                elif station_id not in builder:
                    # create this station
                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        chargers={charger_type: charger_count}
                    )
                elif charger_type in builder[station_id].total_chargers:
                    # combine counts from multiple rows which refer to this charger_type
                    charger_already_loaded = builder[station_id].total_chargers[charger_type]

                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        chargers={charger_type: charger_count + charger_already_loaded}
                    )
                else:
                    # update this station
                    charger_already_loaded = builder[station_id].total_chargers
                    updated_chargers = DictOps.add_to_dict(charger_already_loaded, charger_type, charger_count)

                    return Station.build(
                        id=station_id,
                        geoid=geoid,
                        chargers=updated_chargers
                    )

            except ValueError:
                return IOError(f"unable to parse request {station_id} from row due to invalid value(s): {row}")

    def has_available_charger(self, charger: Charger) -> bool:
        """
        Indicates if a station has an available charge of type `charger`

        :param charger: charger type to be queried.
        :return: Boolean
        """
        if charger in self.total_chargers:
            if self.available_chargers[charger] > 0:
                return True

        return False

    def checkout_charger(self, charger: Charger) -> Optional[Station]:
        """
        Checks out a charger of type `charger` and returns an updated station if there are any available

        :param charger: the charger type to be checked out
        :return: Updated station or None
        """
        chargers = self.available_chargers[charger]

        if chargers < 1:
            return None
        else:
            updated_avail_chargers = self.available_chargers.copy()
            updated_avail_chargers[charger] -= 1

            return self._replace(available_chargers=updated_avail_chargers)

    def return_charger(self, charger: Charger) -> Station:
        """
        Returns a charger of type `charger` to the station.
        Raises exception if available chargers exceeds total chargers

        :param charger: Charger to be returned
        :return: The updated station with returned charger
        """
        chargers = self.available_chargers[charger]
        if (chargers + 1) > self.total_chargers[charger]:
            raise SimulationStateError("Station already has max chargers of this type")
        else:
            updated_avail_chargers = self.available_chargers.copy()
            updated_avail_chargers[charger] += 1

            return self._replace(available_chargers=updated_avail_chargers)
