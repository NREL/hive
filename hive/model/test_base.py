from unittest import TestCase

from h3 import h3

from hive.model.coordinate import Coordinate
from hive.model.station import Station
from hive.model.charger import Charger, ChargerType
from hive.model.base import Base, Stall


class TestStation(TestCase):
    _mock_l2_charger = Charger("charger1",
                               ChargerType.LEVEL_2,
                               7.2,
                               )
    _mock_dcfc_charger = Charger("charger2",
                                 ChargerType.DCFC,
                                 50,
                                 )
    _mock_station = Station("test_station",
                            Coordinate(0, 0),
                            h3.geo_to_h3(0, 0, 11),
                            {_mock_l2_charger.id: _mock_l2_charger, _mock_dcfc_charger.id: _mock_dcfc_charger},
                            )
    _mock_stall = Stall("stall1")
    _mock_base = Base("test_base",
                      Coordinate(0, 0),
                      h3.geo_to_h3(0, 0, 11),
                      _mock_station,
                      {_mock_stall.id: _mock_stall},
                      )

    def test_checkout_stall(self):
        updated_base, stall = self._mock_base.checkout_stall("test_vehicle")

        self.assertEqual(stall.in_use, True)

    def test_checkout_stall_none_avail(self):
        updated_base, stall = self._mock_base.checkout_stall("test_vehicle")

        base_no_stall, no_stall = updated_base.checkout_stall("test_vehicle")

        self.assertIsNone(no_stall)

    def test_return_stall(self):
        updated_base, stall = self._mock_base.checkout_stall("test_vehicle")

        base_w_stall = updated_base.return_stall(stall.id)

        self.assertEqual(base_w_stall.stalls[stall.id].in_use, False)
        self.assertIsNone(base_w_stall.stalls[stall.id].vehicle_id)



