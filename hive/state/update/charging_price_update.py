from __future__ import annotations

import functools as ft
from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Iterator, Dict

from hive.model.energy.charger import Charger
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.dict_reader_stepper import DictReaderStepper
from hive.util.helpers import DictOps
from hive.util.typealiases import GeoId, StationId
from hive.util.units import Currency

from h3 import h3


def default_charging_prices() -> Iterator[Dict[str, str]]:
    """
    used to build the default set of prices
    :return: a price update function which will set all chargers to a Currency of zero
    """
    return iter([{"time": "0",
                  "station_id": "default",
                  "charger_type": charger.value,
                  "price_kw": "0.0"
                  } for charger in Charger.to_tuple()])


class ChargingPriceUpdate(NamedTuple, SimulationUpdateFunction):
    """
    loads charging prices from a file or sets all prices to zero if none provided
    """
    reader: DictReaderStepper
    use_defaults: bool

    @classmethod
    def build(cls,
              charging_file: Optional[str] = None,
              default_values: Iterator[Dict[str, str]] = default_charging_prices()
              ) -> ChargingPriceUpdate:
        """
        reads a requests file and builds a ChargingPriceUpdate SimulationUpdateFunction
        if no charging_file is specified, builds a price update which sets all
        charger types to a kw price of zero Currency units per kw

        :param charging_file: optional file path for charger pricing by time of day
        :param default_values: if file path not provided, this is the fallback
        :return: a SimulationUpdate function pointing at the first line of a request file
        """

        if not charging_file:
            stepper = DictReaderStepper.from_iterator(default_values, "time")
            return ChargingPriceUpdate(stepper, True)
        else:
            req_path = Path(charging_file)
            if not req_path.is_file():
                raise IOError(f"{charging_file} is not a valid path to a request file")
            else:
                stepper = DictReaderStepper.from_file(charging_file, "time")
                return ChargingPriceUpdate(stepper, False)

    def update(self,
               sim_state: SimulationState,
               env: Environment) -> Tuple[SimulationUpdateResult, Optional[ChargingPriceUpdate]]:
        """
        update charging price when the simulation reaches the update's time

        :param sim_state: the current sim state
        :param env: static environment variables
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.current_time

        # parse the most recently available charger price data up to the current sim time
        charger_update, failures = ft.reduce(
            add_row_to_this_update,
            self.reader.read_until_value(current_sim_time),
            ({}, ())
        )

        if len(charger_update) == 0:
            # no update
            return SimulationUpdateResult(sim_state, failures), self

        elif self.use_defaults:
            # we are applying the same values across all Stations
            # the default constructor creates one station_id called "default" and we
            # apply it to every station here.
            result = ft.reduce(
                lambda sim, s_id: update_station_prices(sim, s_id, charger_update['default']),
                sim_state.stations.keys(),
                SimulationUpdateResult(sim_state)
            )
            return result, self

        else:
            # apply update to all stations
            # if these updates are in the form of GeoIds, map them to StationIds
            as_station_updates = map_to_station_ids(charger_update, sim_state)
            station_ids_to_update = set(sim_state.stations.keys()).union(as_station_updates.keys())

            # we are applying only the updates related to valid StationIds with updates
            result = ft.reduce(
                lambda sim, s_id: update_station_prices(sim, s_id, as_station_updates[s_id]),
                station_ids_to_update,
                SimulationUpdateResult(sim_state)
            )
            return result, self


def add_row_to_this_update(acc: Tuple[Dict[str, Dict[Charger, Currency]], Tuple[str, ...]],
                           row: Dict[str, str]) -> Tuple[Dict[str, Dict[Charger, Currency]], Tuple[str, ...]]:
    """
    adds a single row to an accumulator that is storing only the most recently
    observed {StationId|GeoId}/charger/currency combinations

    :param acc: the accumulator
    :param row: the row to add
    :return: the updated accumulator
    """
    rows, failures = acc
    try:
        if "station_id" in row:
            this_entry = rows[row["station_id"]] if rows.get(row["station_id"]) else {}
            this_entry.update({Charger.from_string(row["charger_type"]): float(row["price_kw"])})
            updated = DictOps.add_to_dict(rows,row["station_id"],this_entry)
            return updated, failures
        elif "geoid" in row:
            this_entry = rows[row["geoid"]] if rows.get(row["geoid"]) else {}
            this_entry.update({Charger.from_string(row["charger_type"]): float(row["price_kw"])})
            updated = DictOps.add_to_dict(rows,row["geoid"],this_entry)
            return updated, failures
        else:
            return rows, (f"missing geoid|station_id for row: {row}",) + failures
    except Exception as e:
        return rows, (str(e),)


def update_station_prices(result: SimulationUpdateResult,
                          station_id: StationId,
                          prices_update: Dict[Charger, Currency]) -> SimulationUpdateResult:
    """
    updates a simulation state with prices for a station by station id
    :param result: the simulation state in a partial update state
    :param station_id: the station id of the station to update (assumed to be valid)
    :param prices_update: the prices in Currency that we are updating for each Charger
    :return: the updated SimulationState with station prices modified
    """
    station = result.simulation_state.stations.get(station_id)
    if not station:
        return result
    else:
        updated_station = station.update_prices(prices_update)
        updated_sim = result.simulation_state.modify_station(updated_station)
        if isinstance(updated_sim, Exception):
            # noop for now?
            return result.update_sim(result.simulation_state, str(updated_sim))
        else:
            return result.update_sim(updated_sim)


def map_to_station_ids(this_update: Dict[str, Dict[Charger, Currency]],
                       sim: SimulationState) -> Dict[StationId, Dict[Charger, Currency]]:
    """
    in the case that updates are written by GeoId, map those to StationIds
    :param this_update: the update, which may be by StationId or GeoId
    :param sim: the SimulationState provides h3 resolution and lookup tables
    :return: the price data organized by StationId
    """
    updated = {}
    for k in this_update.keys():
        if k in sim.stations:
            # k is a StationId; leave as is
            updated.update({k: this_update[k]})
        else:
            # k may be a geoid
            try:
                res = h3.h3_get_resolution(k)

                # find the set of all station search geoids corresponding with the
                # provided station charge price geoid
                search_geoids = (k, )
                if res > sim.sim_h3_search_resolution:
                    search_geoids = (h3.h3_to_parent(k, sim.sim_h3_search_resolution), )
                elif res < sim.sim_h3_search_resolution:
                    search_geoids = tuple(h3.h3_to_children(k, sim.sim_h3_search_resolution))
                    search_geoids

                station_ids = (station_id for search_geoid in search_geoids if sim.s_search.get(search_geoid)
                               for station_id in sim.s_search.get(search_geoid))

                # all of these station ids should get entries matching the provided geoid
                for station_id in station_ids:
                    updated.update({station_id: this_update[k]})

            except ValueError as e:
                # todo: handle failure here
                pass

    return updated
