from csv import DictReader
from unittest import TestCase

from hive.resources.mock_lobster import *


class TestBase(TestCase):

    def test_from_row(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,s1"""

        network = mock_network()
        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, network)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertEqual(base.station_id, "s1")

    def test_from_row_no_station(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,"""

        network = mock_network()
        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, network)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertIsNone(base.station_id)

    def test_from_row_none_station(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,none"""

        network = mock_network()
        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, network)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertIsNone(base.station_id)

    def test_checkout_stall(self):
        updated_base = mock_base(stall_count=1).checkout_stall()

        self.assertEqual(updated_base.available_stalls, 0)

    def test_checkout_stall_none_avail(self):
        updated_base = mock_base(stall_count=0)

        base_no_stall = updated_base.checkout_stall()

        self.assertIsNone(base_no_stall)

    def test_return_stall(self):
        updated_base = mock_base(stall_count=1).checkout_stall()

        error, base_w_stall = updated_base.return_stall()

        self.assertEqual(base_w_stall.available_stalls, 1)

    def test_set_membership(self):
        source = """base_id,lat,lon,stall_count,station_id
                            b1,37,122,10,s1"""

        network = mock_network()
        row = next(DictReader(source.split()))

        base = Base.from_row(row, network)

        self.assertTrue(base.membership.public, "should be public")

        base = base.set_membership(('fleet_1', 'fleet_3'))

        self.assertEqual(base.membership.memberships, frozenset(['fleet_1', 'fleet_3']),
                         "should have membership for fleet_1 and fleet_3")
