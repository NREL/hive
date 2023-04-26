from csv import DictReader
from unittest import TestCase

import h3
import immutables


from returns.result import Failure
from nrel.hive.model.station.station import Station

from nrel.hive.resources.mock_lobster import (
    mock_dcfc_charger_id,
    mock_env,
    mock_l1_charger_id,
    mock_l2_charger_id,
    mock_network,
    mock_station,
)


class TestStation(TestCase):
    def test_from_row(self):
        source = """station_id,lat,lon,charger_id,charger_count,on_shift_access
                 s1,37,122,DCFC,10,true
                 """
        network = mock_network()
        env = mock_env()

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row, {}, network, env)

        self.assertEqual(station.id, "s1")
        self.assertEqual(station.geoid, expected_geoid)
        self.assertIsNotNone(station.get_total_chargers(mock_dcfc_charger_id()))
        self.assertEqual(station.get_total_chargers(mock_dcfc_charger_id()), 10)

    def test_from_multiple_rows(self):
        source = """station_id,lat,lon,charger_id,charger_count,on_shift_access
                  s1,37,122,DCFC,10,true
                  s1,37,122,LEVEL_2,5,false
                  """

        network = mock_network()
        env = mock_env()

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, network, env)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, network, env)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIsNotNone(station.get_total_chargers(mock_dcfc_charger_id()))
        self.assertEqual(station2.get_total_chargers(mock_dcfc_charger_id()), 10)
        self.assertIsNotNone(station2.get_total_chargers(mock_l2_charger_id()))
        self.assertEqual(station2.get_total_chargers(mock_l2_charger_id()), 5)

    def test_repeated_charger_id_entry(self):
        source = """station_id,lat,lon,charger_id,charger_count,on_shift_access
                  s1,37,122,DCFC,10,true
                  s1,37,122,DCFC,5,true
                  """

        network = mock_network()
        env = mock_env()

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, network, env)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, network, env)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIsNotNone(station.get_total_chargers(mock_dcfc_charger_id()))
        self.assertEqual(station2.get_total_chargers(mock_dcfc_charger_id()), 15)

    def test_checkout_charger(self):
        error, updated_station = mock_station(
            chargers=immutables.Map({mock_dcfc_charger_id(): 1})
        ).checkout_charger(
            mock_dcfc_charger_id(),
        )
        self.assertIsNone(error, f"should be no error, found {error}")

        self.assertEqual(updated_station.get_available_chargers(mock_dcfc_charger_id()), 0)

    def test_checkout_charger_none_avail(self):
        updated_station = mock_station(chargers=immutables.Map({mock_dcfc_charger_id(): 0}))

        error, no_dcfc_station = updated_station.checkout_charger(mock_dcfc_charger_id())

        self.assertIsNone(error)
        self.assertIsNone(no_dcfc_station)

    def test_return_charger(self):
        station = mock_station(chargers=immutables.Map({mock_l2_charger_id(): 1}))
        err1, updated_station = station.checkout_charger(mock_l2_charger_id())
        self.assertIsNone(err1, "test invariant failed (station has checked out charger)")
        err2, station_w_l2 = updated_station.return_charger(mock_l2_charger_id())
        self.assertIsNone(err2, "should have no error returning charger")
        self.assertEqual(station_w_l2.state[mock_l2_charger_id()].available_chargers, 1)

    def test_set_charger_rate(self):
        station = mock_station()

        new_station = station.set_charger_rate("DCFC", 0.1).unwrap()

        err, charger = new_station.get_charger_instance("DCFC")

        self.assertEqual(charger.rate, 0.1)

    def test_set_charger_rate_too_high(self):
        station = mock_station()

        new_station = station.set_charger_rate("DCFC", 100000)

        self.assertIsInstance(new_station, Failure)

    def test_scale_charger_rate(self):
        station = mock_station()
        err, original_charger = station.get_charger_instance("DCFC")

        new_station = station.scale_charger_rate("DCFC", 0.5).unwrap()

        err, new_charger = new_station.get_charger_instance("DCFC")

        self.assertEqual(original_charger.rate * 0.5, new_charger.rate)

    def test_scale_charger_rate_out_of_bounds(self):
        station = mock_station()

        new_station = station.scale_charger_rate("DCFC", 10)

        self.assertIsInstance(new_station, Failure)

    def test_has_available_charge(self):
        station = mock_station()

        self.assertEqual(
            station.has_available_charger(mock_dcfc_charger_id()),
            True,
            "station should have 1 DCFC charger_id",
        )

    def test_enqueue_for_charger(self):
        station = mock_station(
            chargers={
                mock_l1_charger_id(): 1,
                mock_l2_charger_id(): 1,
                mock_dcfc_charger_id(): 1,
            }
        )

        err1, s1 = station.enqueue_for_charger(mock_dcfc_charger_id())
        err2, s2 = s1.enqueue_for_charger(mock_dcfc_charger_id())
        err3, s3 = s2.enqueue_for_charger(mock_l1_charger_id())

        self.assertIsNone(err1, "should be able to enqueue veh 1")
        self.assertIsNone(err2, "should be able to enqueue veh 2")
        self.assertIsNone(err3, "should be able to enqueue veh 3")

        dc_count = s3.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())
        l1_count = s3.enqueued_vehicle_count_for_charger(mock_l1_charger_id())
        l2_count = s3.enqueued_vehicle_count_for_charger(mock_l2_charger_id())

        self.assertEqual(dc_count, 2, "should have enqueued 2 vehicles for DC charging")
        self.assertEqual(l1_count, 1, "should have enqueued 1 vehicles for Level 1 charging")
        self.assertEqual(l2_count, 0, "should have enqueued 0 vehicles for Level 2 charging")

    def test_dequeue_for_charger(self):
        err1, station = mock_station().enqueue_for_charger(mock_dcfc_charger_id())
        self.assertIsNone(err1, "test invariant failed (should have enqueued vehicle)")

        err2, dequeue_1 = station.dequeue_for_charger(mock_dcfc_charger_id())
        self.assertIsNone(err2, "should be able to dequeue enqueued vehicle")
        dequeue_1_count = dequeue_1.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())
        self.assertEqual(dequeue_1_count, 0, "should have dequeued the single vehicle")

        err3, dequeue_2 = dequeue_1.dequeue_for_charger(mock_dcfc_charger_id())
        self.assertIsNone(dequeue_2, "should not be able to dequeue with empty queue (error)")
        self.assertIsNotNone(err3, "should have an error")

    def test_set_membership(self):
        source = """station_id,lat,lon,charger_id,charger_count,on_shift_access
                         s1,37,122,DCFC,10,true
                         """
        network = mock_network()
        env = mock_env()
        row = next(DictReader(source.split()))

        station = Station.from_row(row, {}, network, env)

        self.assertTrue(station.membership.public, "should be public")

        station = station.set_membership(("fleet_1", "fleet_3"))

        self.assertEqual(
            station.membership.memberships,
            frozenset(["fleet_1", "fleet_3"]),
            "should have membership for fleet_1 and fleet_3",
        )
