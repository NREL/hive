from unittest import TestCase

from hive.state.simulation_state.update.update_requests_from_file import UpdateRequestsFromFile
from hive.resources.mock_lobster import *


class TestUpdateRequests(TestCase):

    def test_update(self):
        """
        test invariant: the below file resource exists
        """
        sim_time = SimTime.build(180)  # will pull in all requests with departure_time earlier than 180
        sim = mock_sim(sim_time=sim_time)
        config = mock_config(
            start_time="2019-01-09T00:00:00",
            end_time="2019-01-10T00:00:00",
        )
        env = mock_env(config, fleet_ids=frozenset())
        req_file = resource_filename("hive.resources.scenarios.denver_downtown.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.scenarios.denver_downtown.service_prices",
                                                "rate_structure.csv")
        fn = UpdateRequestsFromFile.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        self.assertEqual(len(result.requests), 2, "should have added the reqs")
        for req in result.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")

    def test_update_some_aready_cancelled(self):
        """
        won't add requests whos cancel_time has already been exceeded, will instead report them
        test invariant: the below file resource exists
        """
        sim_time = SimTime.build(720)  # will pull in all requests with departure_time earlier than 720
        expected_reqs = 18
        sim = mock_sim(sim_time=sim_time, sim_timestep_duration_seconds=1)
        config = mock_config(
            start_time="2019-01-09T00:00:00",
            end_time="2019-01-10T00:00:00",
        )
        env = mock_env(config, fleet_ids=frozenset())
        req_file = resource_filename("hive.resources.scenarios.denver_downtown.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.scenarios.denver_downtown.service_prices",
                                                "rate_structure.csv")
        fn = UpdateRequestsFromFile.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        self.assertEqual(expected_reqs, len(result.requests), "should have added the reqs")
        for req in result.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")

    def test_update_rate_structure(self):
        """
        won't add requests whos cancel_time has already been exceeded, will instead report them
        test invariant: the below file resource exists
        """
        sim_time = SimTime.build(720)  # will pull in all requests with departure_time earlier than 720
        sim = mock_sim(sim_time=sim_time, sim_timestep_duration_seconds=1)
        config = mock_config(
            start_time="2019-01-09T00:00:00",
            end_time="2019-01-10T00:00:00",
        )
        env = mock_env(config, fleet_ids=frozenset())
        req_file = resource_filename("hive.resources.scenarios.denver_downtown.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.scenarios.denver_downtown.service_prices",
                                                "rate_structure.csv")
        fn = UpdateRequestsFromFile.build(req_file, rate_structure_file)
        result, _ = fn.update(sim, env)
        for req in result.requests.values():
            print(req)
            self.assertGreaterEqual(req.value, 5, f"should be greater/equal than minimum price of 5")

    def test_update_lazy_file_reading(self):
        """
        test invariant: the below file resource exists
        """
        sim_time = SimTime.build(180)  # will pull in all requests with departure_time earlier than 180
        sim = mock_sim(sim_time=sim_time)
        config = mock_config(
            start_time="2019-01-09T00:00:00",
            end_time="2019-01-10T00:00:00",
        )
        env = mock_env(config, fleet_ids=frozenset())
        req_file = resource_filename("hive.resources.scenarios.denver_downtown.requests", "denver_demo_requests.csv")
        rate_structure_file = resource_filename("hive.resources.scenarios.denver_downtown.service_prices",
                                                "rate_structure.csv")
        fn = UpdateRequestsFromFile.build(req_file, rate_structure_file, lazy_file_reading=True)
        result, _ = fn.update(sim, env)
        self.assertEqual(len(result.requests), 2, "should have added the reqs")
        for req in result.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")
