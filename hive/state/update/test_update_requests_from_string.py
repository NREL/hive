from unittest import TestCase

from hive.state.update.update_requests_from_string import UpdateRequestsFromString
from hive.state.simulation_state_ops import initial_simulation_state
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork


class TestUpdateRequestsFromString(TestCase):
    def test_update_single_row(self):
        src = """request_id,origin_x,origin_y,destination_x,destination_y,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        up = UpdateRequestsFromString(src)
        sim, errors = initial_simulation_state(HaversineRoadNetwork(), start_time=61200)

        up_sim = up.update(sim)

        self.assertEquals(len(up_sim.simulation_state.requests), 1, "only one request should have loaded")
        self.assertIn("1_a", up_sim.simulation_state.requests, "the first request should have been added")

    def test_update_second_row_after_first(self):
        """
        invariant: the reader has already consumed its first row
        """
        src = """request_id,origin_x,origin_y,destination_x,destination_y,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        up = UpdateRequestsFromString(src)
        sim, errors = initial_simulation_state(HaversineRoadNetwork(), start_time=61200)

        up_sim = up.update(sim)
        later_sim = up_sim.simulation_state._replace(sim_time=64800)
        up_later_sim = up.update(later_sim)

        self.assertEquals(len(up_later_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertIn("1_b", up_later_sim.simulation_state.requests, "the second request should have been added")

    def test_update_later_time_than_both_requests(self):
        """
        should empty out the parser, which should behave when called afterward
        """
        src = """request_id,origin_x,origin_y,destination_x,destination_y,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        1_b,31.2109091,121.4532226,31.2074449,121.4294263,64800,86399,4
        """
        up = UpdateRequestsFromString(src)
        sim, errors = initial_simulation_state(HaversineRoadNetwork(), start_time=86398)

        up_sim = up.update(sim)

        self.assertEquals(len(up_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertIn("1_a", up_sim.simulation_state.requests, "the first request should have been added")
        self.assertIn("1_b", up_sim.simulation_state.requests, "the second request should have been added")

        later_sim = up_sim.simulation_state._replace(sim_time=86399)
        up_later_sim = up.update(later_sim)

        self.assertEquals(len(up_later_sim.simulation_state.requests), 2, "both requests should have loaded")
        self.assertEquals(up_later_sim.simulation_state.requests,
                          up_sim.simulation_state.requests,
                          "there should be no changes to the requests")
