from unittest import TestCase, skip

from hive.resources.mock_lobster import *


class TestHaversineRoadNetwork(TestCase):
    @skip
    def test_geoid_within_geofence(self):
        somewhere_out_of_geofence = h3.geo_to_h3(0, 0, 15)
        somewhere_within_geofence = h3.geo_to_h3(39.76138151, -104.982001, 15)

        network = mock_network()

        out_of_geofence = network.geoid_within_geofence(somewhere_out_of_geofence)
        within_geofence = network.geoid_within_geofence(somewhere_within_geofence)

        self.assertEqual(out_of_geofence, False, 'should not have found geoid in geofence')
        self.assertEqual(within_geofence, True, 'should have found geoid in geofence')

    def test_route(self):
        """
        Test routing of the haversine roadnetwork
        """
        sim_h3_resolution = 15
        network = mock_network(h3_res=sim_h3_resolution)

        origin = h3.geo_to_h3(37, 122, sim_h3_resolution)
        destination = h3.geo_to_h3(37.01, 122, sim_h3_resolution)
        o = network.position_from_geoid(origin)
        d = network.position_from_geoid(destination)
        route = network.route(o, d)

        self.assertEqual(len(route), 1, "Route should have only one link")
        self.assertEqual(route[0].start, origin, "Route should start from origin")
        self.assertEqual(route[0].end, destination, "Route should end at destination")
        self.assertAlmostEqual(route[0].distance_km, 1.1, places=1, msg="Route should be approx. 1.1km")
