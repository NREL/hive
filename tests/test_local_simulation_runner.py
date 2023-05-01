from unittest import TestCase
from nrel.hive.model.sim_time import SimTime
from nrel.hive.resources.mock_lobster import (
    DefaultIds,
    mock_base,
    mock_config,
    mock_env,
    mock_instruction_generators,
    mock_request,
    mock_sim,
    mock_station,
    mock_update,
    mock_vehicle,
)

from nrel.hive.runner import LocalSimulationRunner
from nrel.hive.runner import RunnerPayload
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.simulation_state.update.cancel_requests import CancelRequests
from nrel.hive.state.simulation_state.update.step_simulation import StepSimulation
from nrel.hive.state.simulation_state.update.update import Update


class TestLocalSimulationRunner(TestCase):
    def test_run(self):
        config = mock_config(end_time=600, timestep_duration_seconds=60)
        env = mock_env(config)
        req = mock_request(request_id="1", departure_time=SimTime.build(0), passengers=2)
        initial_sim = mock_sim(
            vehicles=(mock_vehicle(),),
            stations=(mock_station(),),
            bases=(mock_base(stall_count=5),),
        )

        initial_sim = simulation_state_ops.add_request_safe(initial_sim, req).unwrap()

        update = mock_update()
        runner_payload = RunnerPayload(initial_sim, env, update)

        result = LocalSimulationRunner.run(runner_payload)

        at_destination = result.s.at_geoid(req.destination)
        vehicle = result.s.vehicles[DefaultIds.mock_vehicle_id()]

        self.assertIn(
            DefaultIds.mock_vehicle_id(),
            at_destination["vehicles"],
            "vehicle should have driven request to destination",
        )

        self.assertEqual(
            vehicle.geoid,
            req.destination,
            "Vehicle should be at request destination",
        )

        self.assertAlmostEqual(
            0.56,
            result.s.vehicles[DefaultIds.mock_vehicle_id()].distance_traveled_km,
            places=1,
        )

    def test_step(self):
        config = mock_config()
        env = mock_env(config)
        sim = mock_sim()
        update = Update(
            tuple([CancelRequests()]),
            StepSimulation.from_tuple(mock_instruction_generators(config)),
        )
        runner_payload = RunnerPayload(sim, env, update)

        stepped = LocalSimulationRunner.step(runner_payload)

        self.assertNotEqual(stepped, None, "should have stepped the simulation")

    def test_step_after_end_time(self):
        config = mock_config(end_time=20, start_time=40, timestep_duration_seconds=1)
        env = mock_env(config)
        sim = mock_sim(sim_time=40)
        update = Update(
            tuple([CancelRequests()]),
            StepSimulation.from_tuple(mock_instruction_generators(config)),
        )
        runner_payload = RunnerPayload(sim, env, update)

        stepped = LocalSimulationRunner.step(runner_payload)

        self.assertEqual(
            stepped,
            None,
            "we should not be able to step a simulation that has exceeded end_time",
        )
