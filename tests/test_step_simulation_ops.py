from unittest import TestCase
from nrel.hive.resources.mock_lobster import mock_env, mock_sim, mock_vehicle
from nrel.hive.state.simulation_state.update.step_simulation_ops import (
    perform_vehicle_state_updates,
)


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

        sim = perform_vehicle_state_updates(sim, env)

        vehicle1 = sim.vehicles["1"]
        vehicle2 = sim.vehicles["2"]

        veh1_idle_time = vehicle1.vehicle_state.idle_duration
        veh2_idle_time = vehicle2.vehicle_state.idle_duration

        self.assertEqual(
            veh1_idle_time,
            60,
            "vehicle 1 should have idled for 1 time step (60 s)",
        )
        self.assertEqual(
            veh2_idle_time,
            60,
            "vehicle 2 should have idled for 1 time step (60 s)",
        )
