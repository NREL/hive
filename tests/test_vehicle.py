from csv import DictReader
from unittest import TestCase

from hive.resources.mock_lobster import *


class TestVehicle(TestCase):
    def test_from_row(self):
        source = """vehicle_id,lat,lon,mechatronics_id,initial_soc,schedule_id,home_base_id
                    v1,39.7539,-104.976,bev,1.0,schedule0,b0"""

        row = next(DictReader(source.split()))
        road_network = mock_network()
        env = mock_env()
        expected_geoid = h3.geo_to_h3(39.7539, -104.976, road_network.sim_h3_resolution)

        vehicle = Vehicle.from_row(row, road_network, env)

        self.assertEqual(vehicle.id, "v1")
        self.assertEqual(vehicle.geoid, expected_geoid)
        self.assertEqual(vehicle.mechatronics_id, 'bev')
        self.assertEqual(vehicle.position.geoid, expected_geoid)
        self.assertIsInstance(vehicle.vehicle_state, Idle)
        self.assertEqual(vehicle.distance_traveled_km, 0)

    def test_from_row_bad_mechatronics_id(self):
        source = """vehicle_id,lat,lon,mechatronics_id,initial_soc,schedule_id
                    v1,39.7539,-104.976,beef!@#$,1.0,schedule0"""

        row = next(DictReader(source.split()))
        road_network = mock_network()
        env = mock_env()

        with self.assertRaises(IOError):
            Vehicle.from_row(row, road_network, env)

    def test_set_membership(self):
        source = """vehicle_id,lat,lon,mechatronics_id,initial_soc,schedule_id,home_base_id
                            v1,39.7539,-104.976,bev,1.0,schedule0,hb1"""

        row = next(DictReader(source.split()))
        road_network = mock_network()
        env = mock_env()

        vehicle = Vehicle.from_row(row, road_network, env)

        self.assertTrue(vehicle.membership.public, "should be public")

        vehicle = vehicle.set_membership(('fleet_1', 'fleet_3'))

        self.assertEqual(vehicle.membership.memberships, frozenset(['fleet_1', 'fleet_3']),
                         "should have membership for fleet_1 and fleet_3")
