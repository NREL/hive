from unittest import TestCase

from pkg_resources import resource_filename

from hive.state.update.update_requests import UpdateRequests

from tests.mock_lobster import *


class TestUpdateRequestsFromFile(TestCase):

    def test_update(self):
        """
        test invariant: the below file resource exists
        """
        sim_time = 25380  # will pull in all requests with departure_time earlier than 180
        sim = mock_sim(sim_time=sim_time)
        config = mock_config(
            start_time="2019-01-09T00:00:00-07:00",
            end_time="2019-01-10T00:00:00-07:00",
        )
        env = mock_env(config)
        req_file = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.service_prices", "rate_structure.csv")
        fn = UpdateRequests.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        self.assertEqual(len(result.reports), 2, "should have reported the add")
        self.assertEqual(len(result.simulation_state.requests), 2, "should have added the reqs")
        for req in result.simulation_state.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")

    def test_update_some_aready_cancelled(self):
        """
        won't add requests whos cancel_time has already been exceeded, will instead report them
        test invariant: the below file resource exists
        """
        sim_time = 25920  # will pull in all requests with departure_time earlier than 720
        expected_reqs, expected_reports = 7, 20
        sim = mock_sim(sim_time=sim_time, sim_timestep_duration_seconds=1)
        config = mock_config(
            start_time="2019-01-09T00:00:00-07:00",
            end_time="2019-01-10T00:00:00-07:00",
        )
        env = mock_env(config)
        req_file = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.service_prices", "rate_structure.csv")
        fn = UpdateRequests.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        self.assertEqual(expected_reports, len(result.reports), "should have reported the add")
        self.assertEqual(expected_reqs, len(result.simulation_state.requests), "should have added the reqs")
        for req in result.simulation_state.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")

    def test_update_rate_structure(self):
        """
        won't add requests whos cancel_time has already been exceeded, will instead report them
        test invariant: the below file resource exists
        """
        sim_time = 25920  # will pull in all requests with departure_time earlier than 720
        sim = mock_sim(sim_time=sim_time, sim_timestep_duration_seconds=1)
        config = mock_config(
            start_time="2019-01-09T00:00:00-07:00",
            end_time="2019-01-10T00:00:00-07:00",
        )
        env = mock_env(config)
        req_file = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.service_prices", "rate_structure.csv")
        fn = UpdateRequests.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        for req in result.simulation_state.requests.values():
            print(req)
            self.assertGreaterEqual(req.value, 5, f"should be greater/equal than minimum price of 5")
