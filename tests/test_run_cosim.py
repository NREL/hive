from unittest import TestCase

from hive.app import hive_cosim
from hive.reporting.handler.vehicle_charge_events_handler import (
    VehicleChargeEventsHandler,
)
from hive.resources.mock_lobster import mock_env, mock_sim, mock_update
from hive.runner.runner_payload import RunnerPayload


class TestRunCosim(TestCase):
    def test_load_and_run_denver(self):
        # read scenario
        sim = mock_sim()
        env = mock_env()
        update = mock_update()
        env.reporter.add_handler(VehicleChargeEventsHandler())
        rp0 = RunnerPayload(sim, env, update)
        time_steps = 5

        # crank 5 time steps
        crank_result_1 = hive_cosim.crank(rp0, time_steps=time_steps)
        expected_time = rp0.s.sim_time + (
            time_steps * rp0.s.sim_timestep_duration_seconds
        )
        self.assertEqual(
            crank_result_1.sim_time, expected_time, "expected sim time is incorrect"
        )

        # crank 5 more time steps
        crank_result_2 = hive_cosim.crank(
            crank_result_1.runner_payload, time_steps=time_steps
        )
        expected_time_2 = crank_result_1.runner_payload.s.sim_time + (
            time_steps * rp0.s.sim_timestep_duration_seconds
        )
        self.assertEqual(
            crank_result_2.sim_time, expected_time_2, "expected sim time is incorrect"
        )

