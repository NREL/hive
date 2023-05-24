from __future__ import annotations

import functools as ft
import logging
from csv import DictReader
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple, Optional, Dict

import h3
import immutables

from nrel.hive.model.energy.charger import build_chargers_table
from nrel.hive.model.sim_time import SimTime
from nrel.hive.runner.environment import Environment
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from nrel.hive.util import DictOps
from nrel.hive.util.iterators import DictReaderStepper
from nrel.hive.util.typealiases import StationId, ChargerId
from nrel.hive.util.units import Currency

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargingPriceUpdate(SimulationUpdateFunction):
    """
    loads charging prices from a file or sets all prices to zero if none provided
    """

    reader: DictReaderStepper
    use_defaults: bool

    @classmethod
    def build(
        cls,
        charging_price_file: Optional[str],
        chargers_file: str,
        lazy_file_reading: bool = False,
    ) -> ChargingPriceUpdate:
        """
        reads a requests file and builds a ChargingPriceUpdate SimulationUpdateFunction
        if no charging_file is specified, builds a price update which sets all
        charger_id types to a kw price of zero Currency units per kw


        :param charging_price_file: the optional charging price file provided by the user
        :param chargers_file: the file listing all chargers for this scenario
        :param lazy_file_reading: if true, we load all file data into memory
        :return: a SimulationUpdate function pointing at the first line of a request file
        :raises: an exception if there were file reading issues
        """

        if not charging_price_file:
            # assign default price of $0.00 for any charger types
            table = build_chargers_table(chargers_file)

            def create_default_price(
                acc: Tuple[Dict, ...], charger_id: ChargerId
            ) -> Tuple[Dict, ...]:
                default_price = {
                    "time": "0",
                    "station_id": "default",
                    "charger_id": charger_id,
                    "price_kwh": "0.0",
                }
                return acc + (default_price,)

            initial: Tuple[Dict, ...] = ()
            fallback_values = ft.reduce(create_default_price, table.keys(), initial)
            stepper = DictReaderStepper.from_iterator(
                iter(fallback_values), "time", parser=SimTime.build
            )
            return ChargingPriceUpdate(reader=stepper, use_defaults=True)
        else:
            charging_path = Path(charging_price_file)
            if not charging_path.is_file():
                raise IOError(f"{charging_price_file} is not a valid path to a request file")
            else:
                if lazy_file_reading:
                    error, maybe_stepper = DictReaderStepper.build(
                        charging_path, "time", parser=SimTime.build
                    )
                    if error:
                        raise error
                    elif maybe_stepper is None:
                        raise Exception("Was not able to build DictReaderStepper")
                    else:
                        stepper = maybe_stepper
                else:
                    with charging_path.open() as f:
                        reader = iter(tuple(DictReader(f)))
                    stepper = DictReaderStepper.from_iterator(reader, "time", parser=SimTime.build)

                return ChargingPriceUpdate(stepper, False)

    def update(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[SimulationState, Optional[ChargingPriceUpdate]]:
        """
        update charging price when the simulation reaches the update's time


        :param sim_state: the current sim state
        :param env: static environment variables
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.sim_time

        def stop_condition(value: int) -> bool:
            return value < current_sim_time

        # parse the most recently available charger_id price data up to the current sim time
        initial: immutables.Map[str, immutables.Map[ChargerId, Currency]] = immutables.Map()
        charger_update = ft.reduce(
            _add_row_to_this_update,
            self.reader.read_until_stop_condition(stop_condition),
            initial,
        )

        if len(charger_update) == 0:
            # no update
            return sim_state, self

        elif self.use_defaults:
            # we are applying the same values across all Stations
            # the default constructor creates one station_id called "default" and we
            # apply it to every station here.
            result = ft.reduce(
                lambda sim, s_id: _update_station_prices(sim, s_id, charger_update["default"]),
                sim_state.get_station_ids(),
                sim_state,
            )
            return result, self

        else:
            # apply update to all stations
            # if these updates are in the form of GeoIds, map them to StationIds
            as_station_updates = _map_to_station_ids(charger_update, sim_state)
            station_ids_to_update = set(sim_state.get_station_ids()).union(
                as_station_updates.keys()
            )

            # we are applying only the updates related to valid StationIds with updates
            result = ft.reduce(
                lambda sim, s_id: _update_station_prices(sim, s_id, as_station_updates[s_id]),
                station_ids_to_update,
                sim_state,
            )
            return result, self


def _add_row_to_this_update(
    acc: immutables.Map[str, immutables.Map[ChargerId, Currency]],
    row: Dict[str, str],
) -> immutables.Map[str, immutables.Map[ChargerId, Currency]]:
    """
    adds a single row to an accumulator that is storing only the most recently
    observed {StationId|GeoId}/charger_id/currency combinations


    :param acc: the accumulator
    :param row: the row to add
    :return: the updated accumulator
    """
    rows = acc

    try:
        price = float(row["price_kwh"])
        charger_id = row["charger_id"]
        if "station_id" in row:
            station_id = row["station_id"]
            this_entry = rows[station_id] if rows.get(station_id) else immutables.Map()
            updated = DictOps.add_to_dict(rows, station_id, this_entry.set(charger_id, price))
            return updated
        elif "geoid" in row:
            geoid = row["geoid"]
            this_entry = rows[geoid] if rows.get(geoid) else immutables.Map()
            updated = DictOps.add_to_dict(rows, geoid, this_entry.set(charger_id, price))
            return updated
        else:
            log.error(f"missing geoid|station_id for row: {row}")
            return rows
    except Exception as e:
        log.error(f"error: {e.args} for row {row}")
        return rows


def _update_station_prices(
    simulation_state: SimulationState,
    station_id: StationId,
    prices_update: immutables.Map[ChargerId, Currency],
) -> SimulationState:
    """
    updates a simulation state with prices for a station by station id

    :param result: the simulation state in a partial update state
    :param station_id: the station id of the station to update (assumed to be valid)
    :param prices_update: the prices in Currency that we are updating for each Charger
    :return: the updated SimulationState with station prices modified
    """
    station = simulation_state.stations.get(station_id)
    if not station:
        return simulation_state
    else:
        error, updated_station = station.update_prices(prices_update)
        if error is not None:
            log.error(error)
            return simulation_state
        elif updated_station is None:
            return simulation_state
        else:
            error, updated_sim = simulation_state_ops.modify_station(
                simulation_state, updated_station
            )
            if error:
                log.error(error)
                return simulation_state
            elif updated_sim is None:
                return simulation_state
            else:
                return updated_sim


def _map_to_station_ids(
    this_update: immutables.Map[str, immutables.Map[ChargerId, Currency]],
    sim: SimulationState,
) -> immutables.Map[StationId, immutables.Map[ChargerId, Currency]]:
    """
    in the case that updates are written by GeoId, map those to StationIds

    :param this_update: the update, which may be by StationId or GeoId
    :param sim: the SimulationState provides h3 resolution and lookup tables
    :return: the price data organized by StationId
    """
    updated = {}  # refactor using immutables.Map()?
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
                search_geoids: Tuple[Any, ...] = (k,)
                if res > sim.sim_h3_search_resolution:
                    search_geoids = (h3.h3_to_parent(k, sim.sim_h3_search_resolution),)
                elif res < sim.sim_h3_search_resolution:
                    search_geoids = tuple(h3.h3_to_children(k, sim.sim_h3_search_resolution))

                station_ids = (
                    station_id
                    for search_geoid in search_geoids
                    if sim.s_search.get(search_geoid)
                    for station_id in sim.s_search[search_geoid]
                )

                # all of these station ids should get entries managers the provided geoid
                for station_id in station_ids:
                    updated.update({station_id: this_update[k]})

            except ValueError as e:
                # todo: handle failure here
                log.debug(f"tried to update charging price for key {k} but failed.")

    return immutables.Map(updated)
