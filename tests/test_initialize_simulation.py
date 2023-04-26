from pathlib import Path
from typing import Tuple
import unittest

from pkg_resources import resource_filename

from nrel.hive.app.hive_cosim import crank
from nrel.hive.config.hive_config import HiveConfig
from nrel.hive.config.network import Network
from nrel.hive.dispatcher.instruction.instruction import Instruction
from nrel.hive.dispatcher.instruction.instructions import IdleInstruction
from nrel.hive.initialization.load import load_simulation
from nrel.hive.initialization.initialize_simulation import (
    initialize,
    default_init_functions,
)
from nrel.hive.initialization.initialize_simulation_with_sampling import (
    initialize_simulation_with_sampling,
)
from nrel.hive.resources.mock_lobster import mock_config
from nrel.hive.runner.environment import Environment
from nrel.hive.state.simulation_state.simulation_state import SimulationState

import nrel.hive.state.simulation_state.simulation_state_ops as sso


class TestInitializeSimulation(unittest.TestCase):
    def test_initialize_simulation(self):
        conf = mock_config().suppress_logging()

        sim, env = initialize(conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 1 base")

    def test_initialize_simulation_with_filtering(self):
        conf = mock_config().suppress_logging()

        def filter_veh(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_vehicle_safe(sim, "v1")
            return sim_or_error.unwrap(), env

        def filter_base(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_base_safe(sim, "b1")
            return sim_or_error.unwrap(), env

        def filter_station(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_station_safe(sim, "s1")
            return sim_or_error.unwrap(), env

        init_funtions = default_init_functions()
        init_funtions.extend([filter_veh, filter_base, filter_station])

        sim, env = initialize(conf, init_functions=init_funtions)

        self.assertIsNone(sim.vehicles.get("v1"), "should not have loaded vehicle v1")
        self.assertIsNone(sim.bases.get("b1"), "should not have loaded base b1")
        self.assertIsNone(sim.stations.get("s1"), "should not have loaded station s1")

    def test_load_simulation_with_custom_instruction_function(self):
        conf = mock_config().suppress_logging()

        dummy_instruction1 = IdleInstruction("v1")
        dummy_instruction2 = IdleInstruction("v2")
        dummy_instructions = (dummy_instruction1, dummy_instruction2)

        def custom_instruction_function_1(
            sim: SimulationState, env: Environment
        ) -> Tuple[Instruction, ...]:
            return tuple([dummy_instruction1])

        def custom_instruction_function_2(
            sim: SimulationState, env: Environment
        ) -> Tuple[Instruction, ...]:
            return tuple([dummy_instruction2])

        rp = load_simulation(
            conf,
            custom_instruction_generators=[
                custom_instruction_function_1,
                custom_instruction_function_2,
            ],
        )

        # crank the simulation for 2 steps to make sure we have the
        # applied instructions in the result
        result = crank(rp, 2)

        applied_instructions = tuple(
            sorted(
                result.runner_payload.s.applied_instructions.values(), key=lambda i: i.vehicle_id
            )
        )

        self.assertEqual(
            dummy_instructions, applied_instructions, "should have applied the dummy instructions"
        )

    def test_initialize_simulation_with_sampling(self):
        conf = (
            mock_config()
            ._replace(
                network=Network(
                    network_type="osm_network",
                    default_speed_kmph=40,
                )
            )
            .suppress_logging()
        )

        new_input = conf.input_config._replace(
            road_network_file=Path(
                resource_filename(
                    "nrel.hive.resources.scenarios.denver_downtown.road_network",
                    "downtown_denver_network.json",
                )
            )
        )

        conf = conf._replace(input_config=new_input)

        sim, env = initialize_simulation_with_sampling(
            config=conf,
            vehicle_count=20,
        )
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 2 bases")

    @unittest.skip("makes API call to OpenStreetMaps via osmnx")
    def test_initialize_simulation_load_from_geofence_file(self):
        """Move this to long running if it gets to be out of hand"""
        conf = (
            mock_config()
            ._replace(
                network=Network(
                    network_type="osm_network",
                    default_speed_kmph=40,
                )
            )
            .suppress_logging()
        )

        new_input = conf.input_config._replace(
            geofence_file=Path(
                resource_filename(
                    "nrel.hive.resources.scenarios.denver_downtown.geofence",
                    "downtown_denver.geojson",
                )
            ),
            road_network_file=None,
        )

        conf = conf._replace(input_config=new_input)

        runnerPayload = load_simulation(
            config=conf,
        )
        self.assertIsNotNone(runnerPayload.s.road_network)
