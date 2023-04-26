from unittest import TestCase
import h3

from nrel.hive.dispatcher.instruction.instructions import (
    DispatchStationInstruction,
    DispatchTripInstruction,
)
from nrel.hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from nrel.hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from nrel.hive.resources.mock_lobster import (
    DefaultIds,
    mock_config,
    mock_dcfc_charger_id,
    mock_env,
    mock_membership,
    mock_request_from_geoids,
    mock_sim,
    mock_station_from_geoid,
    mock_vehicle_from_geoid,
)
from nrel.hive.state.simulation_state import simulation_state_ops


class TestInstructionGenerators(TestCase):
    def test_dispatcher_match_vehicle(self):
        dispatcher = Dispatcher(mock_config().dispatcher)

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        near_to_somewhere = h3.geo_to_h3(39.754, -104.975, 15)
        far_from_somewhere = h3.geo_to_h3(39.755, -104.976, 15)

        req = mock_request_from_geoids(origin=somewhere, fleet_id=DefaultIds.mock_membership_id())
        close_veh = mock_vehicle_from_geoid(
            vehicle_id="close_veh",
            geoid=near_to_somewhere,
            membership=mock_membership(),
        )
        far_veh = mock_vehicle_from_geoid(
            vehicle_id="far_veh",
            geoid=far_from_somewhere,
            membership=mock_membership(),
        )
        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(close_veh, far_veh),
        )
        sim = simulation_state_ops.add_request_safe(sim, req).unwrap()

        dispatcher, instructions = dispatcher.generate_instructions(sim, mock_env())

        self.assertGreaterEqual(
            len(instructions),
            1,
            "Should have generated at least one instruction",
        )
        self.assertIsInstance(
            instructions[0],
            DispatchTripInstruction,
            "Should have instructed vehicle to dispatch",
        )
        self.assertEqual(
            instructions[0].vehicle_id,
            close_veh.id,
            "Should have picked closest vehicle",
        )

    def test_dispatcher_no_vehicles(self):
        dispatcher = Dispatcher(mock_config().dispatcher)

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9)
        sim = simulation_state_ops.add_request_safe(sim, req).unwrap()

        dispatcher, instructions = dispatcher.generate_instructions(sim, mock_env())

        self.assertEqual(
            len(instructions),
            0,
            "There are no vehicles to make assignments to.",
        )

    def test_charging_fleet_manager(self):
        charging_fleet_manager = ChargingFleetManager(mock_config().dispatcher)

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.01)

        station = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(veh,),
            stations=(station,),
        )

        (
            charging_fleet_manager,
            instructions,
        ) = charging_fleet_manager.generate_instructions(sim, mock_env())

        self.assertGreaterEqual(
            len(instructions),
            1,
            "Should have generated at least one instruction",
        )
        self.assertIsInstance(
            instructions[0],
            DispatchStationInstruction,
            "Should have instructed vehicle to dispatch to station",
        )

    def test_charging_fleet_manager_queues(self):
        charging_fleet_manager = ChargingFleetManager(mock_config().dispatcher)

        v_geoid = h3.geo_to_h3(39.0, -104.0, 15)
        veh_low_battery = mock_vehicle_from_geoid(geoid=v_geoid, soc=0.01)

        s1_geoid = h3.geo_to_h3(39.01, -104.0, 15)
        s2_geoid = h3.geo_to_h3(39.015, -104.0, 15)  # slightly further away

        # prepare the scenario where the closer station has no
        # available chargers and one enqueued vehicle
        s1 = mock_station_from_geoid(
            station_id="s1",
            geoid=s1_geoid,
            chargers={mock_dcfc_charger_id(): 1},
        )
        e, s1 = s1.checkout_charger(mock_dcfc_charger_id())
        self.assertIsNone(e, "test invariant failed (unable to check out charger at station")
        e, s1 = s1.enqueue_for_charger(mock_dcfc_charger_id())
        self.assertIsNone(
            e,
            "test invariant failed (unable to enqueue for charger at station",
        )
        s2 = mock_station_from_geoid(
            station_id="s2",
            geoid=s2_geoid,
            chargers={mock_dcfc_charger_id(): 1},
        )

        self.assertIsNotNone(s1, "test invariant failed (unable to checkout charger)")

        sim = mock_sim(
            h3_location_res=15,
            h3_search_res=5,
            vehicles=(veh_low_battery,),
            stations=(
                s1,
                s2,
            ),
        )
        env = mock_env()

        (
            charging_fleet_manager,
            instructions,
        ) = charging_fleet_manager.generate_instructions(sim, env)

        self.assertGreaterEqual(
            len(instructions),
            1,
            "Should have generated at least one instruction",
        )
        self.assertIsInstance(
            instructions[0],
            DispatchStationInstruction,
            "Should have instructed vehicle to dispatch to station",
        )
        self.assertEqual(
            instructions[0].station_id,
            s2.id,
            "should have instructed vehicle to go to s2",
        )
