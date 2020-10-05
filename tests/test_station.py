from csv import DictReader
from unittest import TestCase

from tests.mock_lobster import *


class TestStation(TestCase):

    def test_from_row(self):
        source = """station_id,lat,lon,charger_id,charger_count
                 s1,37,122,DCFC,10
                 """
        network = mock_network()

        row = next(DictReader(source.split()))
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row, {}, network)

        self.assertEqual(station.id, "s1")
        self.assertEqual(station.geoid, expected_geoid)
        self.assertIn(mock_dcfc_charger_id(), station.total_chargers)
        self.assertEqual(station.total_chargers[mock_dcfc_charger_id()], 10)

    def test_from_multiple_rows(self):
        source = """station_id,lat,lon,charger_id,charger_count
                  s1,37,122,DCFC,10
                  s1,37,122,LEVEL_2,5
                  """

        network = mock_network()

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, network)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, network)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIn(mock_dcfc_charger_id(), station.total_chargers)
        self.assertEqual(station2.total_chargers[mock_dcfc_charger_id()], 10)
        self.assertIn(mock_l2_charger_id(), station2.total_chargers)
        self.assertEqual(station2.total_chargers[mock_l2_charger_id()], 5)

    def test_repeated_charger_id_entry(self):
        source = """station_id,lat,lon,charger_id,charger_count
                  s1,37,122,DCFC,10
                  s1,37,122,DCFC,5
                  """

        network = mock_network()

        reader = DictReader(source.split())
        row1 = next(reader)
        row2 = next(reader)
        sim_h3_resolution = 15
        expected_geoid = h3.geo_to_h3(37, 122, sim_h3_resolution)

        station = Station.from_row(row1, {}, network)
        builder = {station.id: station}
        station2 = Station.from_row(row2, builder, network)

        self.assertEqual(station2.id, "s1")
        self.assertEqual(station2.geoid, expected_geoid)
        self.assertIn(mock_dcfc_charger_id(), station.total_chargers)
        self.assertEqual(station2.total_chargers[mock_dcfc_charger_id()], 15)

    def test_checkout_charger(self):
        updated_station = mock_station(chargers=immutables.Map({mock_dcfc_charger_id(): 1})).checkout_charger(
            mock_dcfc_charger_id(),
            DefaultIds.mock_vehicle_id(),
        )

        self.assertEqual(updated_station.available_chargers[mock_dcfc_charger_id()], 0)

    def test_checkout_charger_none_avail(self):
        updated_station = mock_station(chargers=immutables.Map({mock_dcfc_charger_id(): 0}))

        no_dcfc_station = updated_station.checkout_charger(mock_dcfc_charger_id(), DefaultIds.mock_vehicle_id())

        self.assertIsNone(no_dcfc_station)

    def test_return_charger(self):
        updated_station = mock_station(chargers=immutables.Map({mock_l2_charger_id(): 1})).checkout_charger(
            mock_l2_charger_id(),
            DefaultIds.mock_vehicle_id(),
        )

        station_w_l2 = updated_station.return_charger(mock_l2_charger_id(), DefaultIds.mock_vehicle_id())

        self.assertEqual(station_w_l2.available_chargers[mock_l2_charger_id()], 1)

    def test_has_available_charge(self):
        station = mock_station()

        self.assertEqual(
            station.has_available_charger(mock_dcfc_charger_id(), DefaultIds.mock_vehicle_id()),
            True,
            'station should have 1 DCFC charger_id',
        )

    def test_enqueue_for_charger(self):
        station = mock_station()
        vid = DefaultIds.mock_vehicle_id()

        has_queues = station.enqueue_for_charger(
            mock_dcfc_charger_id(),
            vid,
        ).enqueue_for_charger(
            mock_dcfc_charger_id(),
            vid,
        ).enqueue_for_charger(
            mock_l1_charger_id(),
            vid,
        )
        dc_count = has_queues.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())
        l1_count = has_queues.enqueued_vehicle_count_for_charger(mock_l1_charger_id())
        l2_count = has_queues.enqueued_vehicle_count_for_charger(mock_l2_charger_id())

        self.assertEqual(dc_count, 2, "should have enqueued 2 vehicles for DC charging")
        self.assertEqual(l1_count, 1, "should have enqueued 1 vehicles for Level 1 charging")
        self.assertEqual(l2_count, 0,  "should have enqueued 0 vehicles for Level 2 charging")

    def test_dequeue_for_charger(self):
        vid = DefaultIds.mock_vehicle_id()
        station = mock_station().enqueue_for_charger(mock_dcfc_charger_id(), vid)

        dequeue_1 = station.dequeue_for_charger(mock_dcfc_charger_id(), vid)
        dequeue_1_count = dequeue_1.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())
        dequeue_2 = dequeue_1.dequeue_for_charger(mock_dcfc_charger_id(), vid)
        dequeue_2_count = dequeue_2.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())

        self.assertEqual(dequeue_1_count, 0, "should have dequeued the single vehicle")
        self.assertEqual(dequeue_2_count, 0, "cannot dequeue to a count below zero")

    def test_private_station(self):
        vid = DefaultIds.mock_vehicle_id()
        other_vid = "nope_private_evs_only"

        station = mock_station(ownership=Ownership(OwnershipType.PRIVATE).add_members((vid,)))

        updated_station = station.checkout_charger(mock_dcfc_charger_id(), vid)
        self.assertIsNotNone(updated_station)

        updated_station = station.enqueue_for_charger(mock_dcfc_charger_id(), vid)
        self.assertIsNotNone(updated_station)

        none_station = station.checkout_charger(mock_dcfc_charger_id(), other_vid)
        self.assertIsNone(none_station)

        none_station = station.enqueue_for_charger(mock_dcfc_charger_id(), other_vid)
        self.assertIsNone(none_station)

