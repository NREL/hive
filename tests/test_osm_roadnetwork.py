from unittest import TestCase, skip

from tests.mock_lobster import *


class TestOSMRoadNetwork(TestCase):
    @skip
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

        origin_point = (39.7481388, -104.9935966)
        destination_point = (39.7613596, -104.981728)

        origin = h3.geo_to_h3(origin_point[0], origin_point[1], sim_h3_resolution)
        destination = h3.geo_to_h3(destination_point[0], destination_point[1], sim_h3_resolution)

        origin_link = network.link_from_geoid(origin)
        destination_link = network.link_from_geoid(destination)

        route = network.route(origin, destination)

        self.assertEqual(origin_link.start, route[0].start, "route should start at origin")
        self.assertEqual(destination_link.end, route[-1].end, "route should end at origin")

    def test_get_nearest_node(self):
        network = mock_osm_network()
        G = network.G

        # first, we find the northern most node
        max_lat = 0
        max_node = None
        for nid in G.nodes():
            lat = G.nodes[nid]['y']
            if lat > max_lat:
                max_lat = lat
                max_node = nid

        node = network.G.nodes[max_node]

        nearest_node = network.get_nearest_node(node['y']+0.5, node['x'])

        self.assertEqual(max_node, nearest_node, "node should be nearest to itself")
