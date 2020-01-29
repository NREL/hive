from unittest import TestCase

from hive.state.update.update_requests_from_string import UpdateRequestsFromString
from tests.mock_lobster import *


class TestUpdateRequestsFromString(TestCase):
    def test_update_single_row(self):
        src = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        fn = UpdateRequestsFromString.build(src)
        sim = mock_sim(sim_time=61200)
        env = mock_env()

        up_sim, _ = fn.update(sim, env)

        self.assertEquals(len(up_sim.simulation_state.requests), 1, "only one request should have loaded")
        self.assertIn("1_a", up_sim.simulation_state.requests, "the first request should have been added")

    def test_update_second_row_after_first(self):
        """
        invariant: the reader has already consumed its first row
        """
        src = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        fn1 = UpdateRequestsFromString.build(src)
        sim = mock_sim(sim_time=61200)
        env = mock_env()

        up_sim, fn2 = fn1.update(sim, env)
        later_sim = up_sim.simulation_state._replace(sim_time=64800)
        up_later_sim, _ = fn2.update(later_sim, env)

        self.assertEquals(len(up_later_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertIn("1_b", up_later_sim.simulation_state.requests, "the second request should have been added")

    def test_update_later_time_than_both_requests(self):
        """
        should empty out the parser, which should behave when called afterward
        """
        src = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,86399,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        fn1 = UpdateRequestsFromString.build(src)
        sim = mock_sim(sim_time=86398)
        env = mock_env()

        up_sim, fn2 = fn1.update(sim, env)

        self.assertEquals(len(up_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertIn("1_a", up_sim.simulation_state.requests, "the first request should have been added")
        self.assertIn("1_b", up_sim.simulation_state.requests, "the second request should have been added")

        later_sim = up_sim.simulation_state._replace(sim_time=86399)
        up_later_sim, _ = fn2.update(later_sim, env)

        self.assertEquals(len(up_later_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertEquals(up_later_sim.simulation_state.requests,
                          up_sim.simulation_state.requests,
                          "there should be no changes to the requests")
