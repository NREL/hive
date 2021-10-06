from unittest import TestCase, skip

from hive.resources.mock_lobster import *


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

        o_lat, o_lon = (39.7481388, -104.9935966)
        d_lat, d_lon = (39.7613596, -104.981728)

        origin = h3.geo_to_h3(o_lat, o_lon, sim_h3_resolution)
        destination = h3.geo_to_h3(d_lat, d_lon, sim_h3_resolution)

        origin_position = network.position_from_geoid(origin)
        destination_position = network.position_from_geoid(destination)
        route = network.route(origin_position, destination_position)

        self.assertEqual(origin_position.link_id, route[0].link_id, "origin link id should be first route link id")
        self.assertEqual(destination_position.link_id, route[-1].link_id, "destination link id should be the last route link id")
        self.assertEqual(origin_position.geoid, route[0].start, "route should start at origin GeoId (stationary road network location)")
        self.assertEqual(destination_position.geoid, route[-1].end, "route should end at destination GeoId (stationary road network location)")
