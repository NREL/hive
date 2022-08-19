from unittest import TestCase

from returns.result import Success

from hive.state.simulation_state.update.cancel_requests import CancelRequests
from hive.resources.mock_lobster import *


class TestCancelRequests(TestCase):
    def test_update_cancellable(self):
        req = mock_request()
        sim_or_err = simulation_state_ops.add_request_safe(mock_sim(sim_time=600), req)
        self.assertIsInstance(sim_or_err, Success)
        sim = sim_or_err.unwrap()
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertNotIn(req.id, result.requests, "request should have been removed")
        self.assertNotIn(req.origin, result.r_locations, "request location should have been removed")

    def test_update_not_cancellable(self):
        req = mock_request()
        sim_or_err = simulation_state_ops.add_request_safe(mock_sim(sim_time=599), req)
        self.assertIsInstance(sim_or_err, Success)
        sim = sim_or_err.unwrap()
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertIn(req.id, result.requests, "request should not have been removed")
        self.assertIn(req.origin, result.r_locations, "request location should not have been removed")

