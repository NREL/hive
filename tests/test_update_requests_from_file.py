from unittest import TestCase, skip

from pkg_resources import resource_filename

from hive.state.update.update_requests_from_file import UpdateRequestsFromFile

from tests.mock_lobster import *


class TestUpdateRequestsFromFile(TestCase):

    def test_update(self):
        """
        test invariant: the below file resource exists
        """
        sim_time = 3  # will pull in all requests with departure_time earlier than 3
        sim = mock_sim(sim_time=sim_time)
        req_file = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        fn = UpdateRequestsFromFile.build(req_file)
        result, _ = fn.update(sim)
        self.assertEqual(len(result.reports), 2, "should have reported the add")
        self.assertEqual(len(result.simulation_state.requests), 2, "should have added the reqs")
        for req in result.simulation_state.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")

    def test_update_some_aready_cancelled(self):
        """
        won't add requests whos cancel_time has already been exceeded, will instead report them
        test invariant: the below file resource exists
        """
        sim_time = 12  # will pull in all requests with departure_time earlier than 12
        expected_reqs, expected_reports = 7, 20
        sim = mock_sim(sim_time=sim_time)
        req_file = resource_filename("hive.resources.requests", "denver_demo_requests.csv")
        fn = UpdateRequestsFromFile.build(req_file)
        result, _ = fn.update(sim)
        self.assertEqual(len(result.reports), expected_reports, "should have reported the add")
        self.assertEqual(len(result.simulation_state.requests), expected_reqs, "should have added the reqs")
        for req in result.simulation_state.requests.values():
            self.assertLess(req.departure_time, sim_time, f"should be less than {sim_time}")
