import csv
import functools as ft
from pathlib import Path
from typing import Dict, Tuple, Any

from returns.io import IOResult, IOResultE

from nrel.hive.model.station.station import Station
from nrel.hive.runner import Environment
from nrel.hive.state.simulation_state.simulation_state import SimulationState


def log_station_capacities(sim: SimulationState, env: Environment) -> IOResultE[Path]:
    """
    logs each station and it's load capacity to the output directory


    :param sim: the (initial) simulation state
    :param env: the environment with a Reporter instance
    :return: nothing, or, any exception
    """

    def _station_energy(station: Station) -> Dict[str, Any]:
        """
        get the Kw capacity of a given station

        :param station: the station to observe
        :return: the capacity of this station as a CSV row dictionary
        """
        # TODO: now that we've introduced other energy types, we should return a summary of charger rate by
        #  energy time with corresponding units - ndr
        rate: float = ft.reduce(
            lambda acc, cs: acc + cs.total_chargers * cs.charger.rate,
            station.state.values(),
            0.0,
        )

        return {"station_id": station.id, "rate": rate}

    try:
        result: Tuple[Dict[str, Any], ...] = ft.reduce(
            lambda acc, s: acc + (_station_energy(s),),
            sim.get_stations(),
            (),
        )

        output_file = Path(env.config.scenario_output_directory).joinpath("station_capacities.csv")
        with output_file.open("w") as f:
            writer = csv.DictWriter(f, fieldnames=["station_id", "rate"])
            writer.writeheader()
            writer.writerows(result)

        return IOResult.from_value(output_file)

    except Exception as e:
        return IOResult.from_failure(e)
