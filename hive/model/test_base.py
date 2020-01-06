from csv import DictReader
from unittest import TestCase

from h3 import h3

from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.station import Station
from hive.model.energy.charger import Charger
from hive.model.base import Base


class TestBase(TestCase):
    _mock_station = Station.build("test_station",
                                  h3.geo_to_h3(0, 0, 11),
                                  {Charger.LEVEL_2: 1, Charger.DCFC: 1},
                                  )

    _mock_base = Base.build("test_base",
                            h3.geo_to_h3(0, 0, 11),
                            _mock_station,
                            1,
                            )

    def test_from_row(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,s1"""

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, sim_h3_resolution)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertEqual(base.station_id, "s1")

    def test_from_row_no_station(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,"""

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, sim_h3_resolution)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertIsNone(base.station_id)

    def test_from_row_none_station(self):
        source = """base_id,lat,lon,stall_count,station_id
                    b1,37,122,10,none"""

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        base = Base.from_row(row, sim_h3_resolution)

        self.assertEqual(base.id, "b1")
        self.assertEqual(base.geoid, expected_geoid)
        self.assertEqual(base.total_stalls, 10)
        self.assertIsNone(base.station_id)

    def test_checkout_stall(self):
        updated_base = self._mock_base.checkout_stall()

        self.assertEqual(updated_base.available_stalls, 0)

    def test_checkout_stall_none_avail(self):
        updated_base = self._mock_base.checkout_stall()

        base_no_stall = updated_base.checkout_stall()

        self.assertIsNone(base_no_stall)

    def test_return_stall(self):
        updated_base = self._mock_base.checkout_stall()

        base_w_stall = updated_base.return_stall()

        self.assertEqual(base_w_stall.available_stalls, 1)
