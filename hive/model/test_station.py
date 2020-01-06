from csv import DictReader
from unittest import TestCase

from h3 import h3

from hive.model.station import Station
from hive.model.energy.charger import Charger


class TestStation(TestCase):
    _mock_station = Station.build("test_station",
                                  h3.geo_to_h3(0, 0, 11),
                                  {Charger.LEVEL_2: 1, Charger.DCFC: 1},
                                  )

    def test_from_row(self):
        source = """station_id,lat,lon,charger_type,charger_count
                 s1,37,122,DCFC,10
                 """

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row, {}, sim_h3_resolution)

        self.assertEqual(station.id, "s1")
        self.assertEqual(station.geoid, expected_geoid)
        self.assertIn(Charger.DCFC, station.total_chargers)
        self.assertEqual(station.total_chargers[Charger.DCFC], 10)

    def test_from_multiple_rows(self):
        source = """station_id,lat,lon,charger_type,charger_count
                  s1,37,122,DCFC,10
                  s1,37,122,LEVEL_2,5
                  """

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, sim_h3_resolution)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, sim_h3_resolution)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIn(Charger.DCFC, station.total_chargers)
        self.assertEqual(station2.total_chargers[Charger.DCFC], 10)
        self.assertIn(Charger.LEVEL_2, station2.total_chargers)
        self.assertEqual(station2.total_chargers[Charger.LEVEL_2], 5)

    def test_repeated_charger_type_entry(self):
        source = """station_id,lat,lon,charger_type,charger_count
                  s1,37,122,DCFC,10
                  s1,37,122,DCFC,5
                  """

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, sim_h3_resolution)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, sim_h3_resolution)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIn(Charger.DCFC, station.total_chargers)
        self.assertEqual(station2.total_chargers[Charger.DCFC], 15)

    def test_checkout_charger(self):
        updated_station = self._mock_station.checkout_charger(Charger.DCFC)

        self.assertEqual(updated_station.available_chargers[Charger.DCFC], 0)

    def test_checkout_charger_none_avail(self):
        updated_station = self._mock_station.checkout_charger(Charger.DCFC)

        no_dcfc_station = updated_station.checkout_charger(Charger.DCFC)

        self.assertIsNone(no_dcfc_station)

    def test_return_charger(self):
        updated_station = self._mock_station.checkout_charger(Charger.LEVEL_2)

        station_w_l2 = updated_station.return_charger(Charger.LEVEL_2)

        self.assertEqual(station_w_l2.available_chargers[Charger.LEVEL_2], 1)
