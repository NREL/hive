from unittest import TestCase
from hive.state.simulation_state.update.step_simulation_ops import step_vehicle
from hive.resources.mock_lobster import *


class TestStepSimulationOps(TestCase):
    def test_step_vehicle(self):
        """
        build a sim with two idle vehicles and only step one of them for 10 time steps (600 seconds)

        check to make sure only one of them idled.
        """
        vehicle1 = mock_vehicle(vehicle_id="1")
        vehicle2 = mock_vehicle(vehicle_id="2")
        sim = mock_sim(vehicles=(vehicle1, vehicle2))
        env = mock_env()

        for _ in range(10):
            err, sim = step_vehicle(sim, env, vehicle_id="2")
            if err is not None:
                self.fail(err)

        vehicle1: Vehicle = sim.vehicles.get("1")
        vehicle2: Vehicle = sim.vehicles.get("2")

        veh1_idle_time = vehicle1.vehicle_state.idle_duration
        veh2_idle_time = vehicle2.vehicle_state.idle_duration

        self.assertEqual(veh1_idle_time, 0, "vehicle 1 should not have idled")
        self.assertEqual(veh2_idle_time, 600,
                         "vehicle 2 should have idled for 10 time steps (600 s)")

    # @unittest.skip("refactor so that we aren't injecting VehicleState into vehicles which bypasses VehicleState.enter op")
    def test_step_vehicle_state_change(self):
        """
        build a sim with two charging vehicles and only step one of them until done charging.

        check to make sure only one vehicle transitioned from the charging state to the idle state.
        """
        self.skipTest(
            "refactor so that we aren't injecting VehicleState into vehicles. doing so " 
            "bypasses the VehicleState.enter method, which in this case will lead to an "
            "unexpected behavior when these vehicles return chargers that they never checked "
            "out in the first place."
        )
        station = mock_station("s1")
        vehicle1 = mock_vehicle(
            vehicle_id="1",
            vehicle_state=ChargingStation.build("1", "s1", mock_dcfc_charger_id()),
        )
        vehicle2 = mock_vehicle(
            vehicle_id="2",
            vehicle_state=ChargingStation.build("2", "s1", mock_dcfc_charger_id()),
        )
        sim = mock_sim(vehicles=(vehicle1, vehicle2), stations=(station, ))
        env = mock_env()

        for _ in range(10):
            err, sim = step_vehicle(sim, env, vehicle_id="2")
            if err is not None:
                self.fail(err)

        vehicle1: Vehicle = sim.vehicles.get("1")
        vehicle2: Vehicle = sim.vehicles.get("2")

        veh1_state = vehicle1.vehicle_state
        veh2_state = vehicle2.vehicle_state

        self.assertIsInstance(veh1_state, ChargingStation,
                              "vehicle 1 should still be in charging state")
        self.assertIsInstance(veh2_state, Idle, "vehicle 2 should have transitioned to idle")
