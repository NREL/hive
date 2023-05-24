from unittest import TestCase
from nrel.hive.model.sim_time import SimTime
from nrel.hive.resources.mock_lobster import mock_env, mock_osm_network, mock_request, mock_sim

from nrel.hive.state.simulation_state.update.update_requests_sampling import UpdateRequestsSampling


class TestUpdateRequestsSampling(TestCase):
    def test_update(self):
        sim = mock_sim(
            sim_time=SimTime.build(180),
            road_network=mock_osm_network(),
        )
        env = mock_env()

        requests = tuple(mock_request(request_id=str(i)) for i in range(5))

        fn = UpdateRequestsSampling.build(sampled_requests=requests)
        result, _ = fn.update(sim, env)
        self.assertEqual(len(result.requests), 5, "should have added 5 requests")

        for r in result.get_requests():
            self.assertNotEqual(
                r.origin,
                r.destination,
                "origin and destination should not be equal",
            )
