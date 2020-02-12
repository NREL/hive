from unittest import TestCase

from hive.runner import RunnerPayload
from hive.state.update.cancel_requests import CancelRequests

from tests.mock_lobster import *
from hive.runner import LocalSimulationRunner


class TestLocalSimulationRunner(TestCase):

    def test_run(self):
        config = mock_config(end_time=20, timestep_duration_seconds=1)
        env = mock_env(config)
        req = mock_request(
            request_id='1',
            o_lat=-37.001,
            o_lon=122,
            d_lat=-37.1,
            d_lon=122,
            departure_time=0,
            cancel_time=3600,
            passengers=2
        )
        initial_sim = mock_sim(
            vehicles=(mock_vehicle(lat=-37, lon=122, capacity_kwh=100, ideal_energy_limit_kwh=None),),
            stations=(mock_station(lat=-36.999, lon=122),),
            bases=(mock_base(stall_count=5, lat=-37, lon=121.999),),
        ).add_request(req)

        update = mock_update()
        runner_payload = RunnerPayload(initial_sim, env, update)

        result = LocalSimulationRunner.run(runner_payload)

        at_destination = result.s.at_geoid(req.destination)
        self.assertIn(DefaultIds.mock_vehicle_id(), at_destination['vehicles'],
                      "vehicle should have driven request to destination")

        self.assertAlmostEqual(11.1, result.s.vehicles[DefaultIds.mock_vehicle_id()].distance_traveled_km, places=1)

    def test_step(self):
        config = mock_config()
        env = mock_env(config)
        sim = mock_sim()
        update = Update((CancelRequests()), StepSimulation(default_dispatcher(config)))
        runner_payload = RunnerPayload(sim, env, update)

        stepped = LocalSimulationRunner.step(runner_payload)

        self.assertNotEqual(stepped, None, "should have stepped the simulation")

    def test_step_after_end_time(self):
        config = mock_config(end_time=20, start_time=40, timestep_duration_seconds=1)
        env = mock_env(config)
        sim = mock_sim(sim_time=40)
        update = Update((CancelRequests()), StepSimulation(default_dispatcher(config)))
        runner_payload = RunnerPayload(sim, env, update)

        stepped = LocalSimulationRunner.step(runner_payload)

        self.assertEqual(stepped, None, "we should not be able to step a simulation that has exceeded end_time")