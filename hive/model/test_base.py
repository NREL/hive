from unittest import TestCase

from h3 import h3

from hive.model.coordinate import Coordinate
from hive.model.station import Station
from hive.model.charger import Charger
from hive.model.base import Base


class TestBase(TestCase):
    _mock_station = Station.build("test_station",
                                  Coordinate(0, 0),
                                  h3.geo_to_h3(0, 0, 11),
                                  {Charger.LEVEL_2: 1, Charger.DCFC: 1},
                                  )

    _mock_base = Base.build("test_base",
                            Coordinate(0, 0),
                            h3.geo_to_h3(0, 0, 11),
                            _mock_station,
                            1,
                            )

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
