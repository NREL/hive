from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict
from nrel.hive.util.typealiases import VehicleId
from nrel.hive.reporting.handler.handler import Handler
from nrel.hive.reporting.handler.kepler_feature import KeplerFeature

if TYPE_CHECKING:
    from nrel.hive.runner.runner_payload import RunnerPayload
    from nrel.hive.reporting.reporter import Report

PREFIX = """
{
"type": "FeatureCollection",
"features": [
"""

SUFIX = """
]
}
"""


class KeplerHandler(Handler):
    """
    handles events and appends them to the event.log output file based on global logging settings
    """

    def __init__(self, scenario_output_directory: Path) -> None:
        """
        Create the Kepler Handler to generate a kepler.json file for Kepler.gl

        :param scenario_output_directory: path to the output directory
            where kepler.json will be written
        """
        log_path = scenario_output_directory / "kepler.json"
        self.log_file = open(log_path, "a")
        self.log_file.write(PREFIX)
        self.kepler_features: Dict[VehicleId, KeplerFeature] = {}
        self.first_feature = True

    def handle(self, reports: List[Report], runner_payload: RunnerPayload) -> None:
        """
        Capture the current states/locations of all vehicles and save in
        the in memory Dict and write complete trips to the kepler.json file
        """
        sim_state = runner_payload.s

        for vehicle in sim_state.get_vehicles():
            try:
                kepler_feature = self.kepler_features[vehicle.id]
            except KeyError:
                kepler_feature = KeplerFeature(
                    vehicle.id, vehicle.vehicle_state.__class__.__name__, sim_state.sim_time
                )
                self.kepler_features[vehicle.id] = kepler_feature

            # A completed Kepler "Feature" happens when the vehicle changes states
            if kepler_feature.state != vehicle.vehicle_state.__class__.__name__:
                if not self.first_feature:
                    self.log_file.write(",\n")
                else:
                    self.first_feature = False
                json.dump(kepler_feature.gen_json(), self.log_file)
                # clear out the old coordinates and start a new "Feature"
                kepler_feature.reset(vehicle.vehicle_state.__class__.__name__, sim_state.sim_time)

            kepler_feature.add_coord(vehicle.geoid, sim_state.sim_time)

    def close(self, runner_payload: RunnerPayload) -> None:
        """
        Grab the final states/locations of all of the vehicles and write them to the kepler.json
        """
        for kepler_feature in self.kepler_features.values():
            if not self.first_feature:
                self.log_file.write(",\n")
            else:
                self.first_feature = False
            json.dump(kepler_feature.gen_json(), self.log_file)
        self.log_file.write(SUFIX)
        self.log_file.close()
