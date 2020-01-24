from unittest import TestCase

from hive.state.update.cancel_requests import CancelRequests
from tests.mock_lobster import *


class TestCancelRequests(TestCase):
    def test_update_cancellable(self):
        req = mock_request(cancel_time=600)
        sim = mock_sim(sim_time=600).add_request(req)
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertNotIn(req.id, result.simulation_state.requests, "request should have been removed")
        self.assertNotIn(req.origin, result.simulation_state.r_locations, "request location should have been removed")
        self.assertEqual(len(result.reports), 1, "should have produced a cancellation report")

    def test_update_not_cancellable(self):
        req = mock_request(cancel_time=600)
        sim = mock_sim(sim_time=599).add_request(req)
        env = mock_env()
        cancel_requests = CancelRequests()
        result, _ = cancel_requests.update(sim, env)
        self.assertIn(req.id, result.simulation_state.requests, "request should not have been removed")
        self.assertIn(req.origin, result.simulation_state.r_locations, "request location should not have been removed")

