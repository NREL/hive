from unittest import TestCase

from h3 import h3

from hive.model.station import Station
from hive.model.energy.charger import Charger


class TestStation(TestCase):
    _mock_station = Station.build("test_station",
                            h3.geo_to_h3(0, 0, 11),
                            {Charger.LEVEL_2: 1, Charger.DCFC: 1},
                            )

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



