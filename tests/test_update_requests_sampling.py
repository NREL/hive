from unittest import TestCase

from hive.state.simulation_state.update.update_requests_sampling import UpdateRequestsSampling
from tests.mock_lobster import *


class TestUpdateRequestsSampling(TestCase):

    def test_update_default_sampling(self):
        """
        default sampler just adds N_Vehicles/4 random requests into the sim at each timestep
        :return:
        """

        #  sim with 12 vehicles
        sim = mock_sim(
            vehicles=tuple(mock_vehicle(vehicle_id=str(i)) for i in range(12)),
            road_network=mock_osm_network(),
        )
        env = mock_env()

        fn = UpdateRequestsSampling.build()
        result, _ = fn.update(sim, env)
        self.assertEqual(len(result.requests), 3, "should have added 12/4 = 3 requests")

        for r in result.requests.values():
            self.assertNotEqual(r.origin, r.destination, "origin and destination should not be equal")

