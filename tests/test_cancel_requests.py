from unittest import TestCase

from hive.state.simulation_state.update.cancel_requests import CancelRequests
from tests.mock_lobster import *


class TestCancelRequests(TestCase):
    def test_update_cancellable(self):
        req = mock_request()
        _, sim = simulation_state_ops.add_request(mock_sim(sim_time=600), req)
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertNotIn(req.id, result.requests, "request should have been removed")
        self.assertNotIn(req.origin, result.r_locations, "request location should have been removed")

    def test_update_not_cancellable(self):
        req = mock_request()
        _, sim = simulation_state_ops.add_request(mock_sim(sim_time=599), req)
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertIn(req.id, result.requests, "request should not have been removed")
        self.assertIn(req.origin, result.r_locations, "request location should not have been removed")

