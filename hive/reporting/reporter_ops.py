import csv
import functools as ft
from pathlib import Path
from typing import Tuple

import immutables
from returns.io import IOResult, IOResultE

from hive.model.station import Station
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util import Kw


def log_station_capacities(sim: SimulationState, env: Environment) -> IOResultE[Path]:
    """
    logs each station and it's load capacity to the output directory

    :param sim: the (initial) simulation state
    :param env: the environment with a Reporter instance
    :return: nothing, or, any exception
    """
    def _station_energy(station: Station) -> dict:
        """
        get the Kw capacity of a given station
        :param station: the station to observe
        :return: the capacity of this station as a CSV row dictionary
        """
        capacity_kw: Kw = ft.reduce(
            lambda acc, charger_id: acc + station.total_chargers.get(charger_id) * env.chargers.get(charger_id).power_kw,
            station.available_chargers.keys(),
            0.0
        )

        return {'station_id': station.id, 'capacity_kw': capacity_kw}

    try:
        result: Tuple[immutables.Map, ...] = ft.reduce(
            lambda acc, s: acc + (_station_energy(s),),
            sim.stations.values(),
            ()
        )

        output_file = Path(env.config.scenario_output_directory).joinpath("station_capacities.csv")
        with output_file.open('w') as f:
            writer = csv.DictWriter(f, fieldnames=['station_id', 'capacity_kw'])
            writer.writeheader()
            writer.writerows(result)

        return IOResult.from_value(output_file)

    except Exception as e:
        return IOResult.from_failure(e)
