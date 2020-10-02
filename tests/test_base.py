from csv import DictReader
from unittest import TestCase

from tests.mock_lobster import *


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
        updated_base = mock_base(stall_count=1).checkout_stall(DefaultIds.mock_vehicle_id())

        self.assertEqual(updated_base.available_stalls, 0)

    def test_checkout_stall_none_avail(self):
        updated_base = mock_base(stall_count=0)

        base_no_stall = updated_base.checkout_stall(DefaultIds.mock_vehicle_id())

        self.assertIsNone(base_no_stall)

    def test_return_stall(self):
        updated_base = mock_base(stall_count=1).checkout_stall(DefaultIds.mock_vehicle_id())

        base_w_stall = updated_base.return_stall(DefaultIds.mock_vehicle_id())

        self.assertEqual(base_w_stall.available_stalls, 1)

    def test_private_ownership(self):
        vid = DefaultIds.mock_vehicle_id()

        base = mock_base(
            stall_count=1,
            ownership=Ownership(OwnershipType.PRIVATE).add_member(vid)
        )

        updated_base = base.checkout_stall(vid)

        self.assertEqual(updated_base.available_stalls, 0)

    def test_bad_private_ownership(self):
        vid = DefaultIds.mock_vehicle_id()
        other_vid = "vehicle_trying_to_park_in_someone_elses_garage"

        base = mock_base(
            stall_count=1,
            ownership=Ownership(OwnershipType.PRIVATE).add_member(vid)
        )

        updated_base = base.checkout_stall(other_vid)

        self.assertIsNone(updated_base)

