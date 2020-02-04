from unittest import TestCase, skip

from tests.mock_lobster import *


class TestHaversineRoadNetwork(TestCase):
    @skip("Test not implemented yet")
    def test_geoid_within_geofence(self):
        pass

    @skip("Test not implemented yet")
    def test_link_id_within_geofence(self):
        pass

    @skip("Test not implemented yet")
    def test_geoid_within_simulation(self):
        pass

    def test_route(self):
        """
        Test routing of the haversine roadnetwork
        """
        sim_h3_resolution = 15
        network = mock_network(h3_res=sim_h3_resolution)

        origin = h3.geo_to_h3(37, 122, sim_h3_resolution)
        destination = h3.geo_to_h3(37.01, 122, sim_h3_resolution)

        start = network.property_link_from_geoid(origin)
        end = network.property_link_from_geoid(destination)

        route = network.route(start, end)

        self.assertEqual(len(route), 1, "Route should have only one link")
        self.assertEqual(route[0].start, origin, "Route should start from origin")
        self.assertEqual(route[0].end, destination, "Route should end at destination")
        self.assertAlmostEqual(route[0].distance_km, 1.1, places=1, msg="Route should be approx. 1.1km")





