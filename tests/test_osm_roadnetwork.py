from unittest import TestCase

from tests.mock_lobster import *


class TestOSMRoadNetwork(TestCase):
    def test_geoid_within_geofence(self):
        somewhere_out_of_geofence = h3.geo_to_h3(0, 0, 15)
        somewhere_within_geofence = h3.geo_to_h3(39.76138151, -104.982001, 15)

        network = mock_osm_network()

        out_of_geofence = network.geoid_within_geofence(somewhere_out_of_geofence)
        within_geofence = network.geoid_within_geofence(somewhere_within_geofence)

        self.assertEqual(out_of_geofence, False, 'should not have found geoid in geofence')
        self.assertEqual(within_geofence, True, 'should have found geoid in geofence')

    def test_route(self):
        sim_h3_resolution = 15
        network = mock_osm_network(h3_res=sim_h3_resolution)

        # points chosen to lie exactly on the road network
        origin_point = (39.7481388, -104.9935966)
        destination_point = (39.7613596, -104.981728)

        origin = h3.geo_to_h3(origin_point[0], origin_point[1], sim_h3_resolution)
        destination = h3.geo_to_h3(destination_point[0], destination_point[1], sim_h3_resolution)

        route = network.route(origin, destination)

        self.assertEqual(origin, route[0].start, "route should start at origin")
        self.assertEqual(destination, route[-1].end, "route should end at origin")
