import unittest
from csv import DictReader

from hive.model.passenger import create_passenger_id
from tests.mock_lobster import *


class MyTestCase(unittest.TestCase):
    request_id = "test"
    origin = h3.geo_to_h3(0, 0, res=11)
    destination = h3.geo_to_h3(3, 4, res=11)
    departure_time = 28800
    cancel_time = 29400
    passengers = 2

    request = mock_request(
        request_id=request_id,
        o_lat=0,
        o_lon=0,
        d_lat=3,
        d_lon=4,
        h3_res=11,
        departure_time=28800,
        cancel_time=29400,
        passengers=2
    )

    def test_request_constructor(self):
        """
        the constructed request should not modify its arguments
        """
        self.assertEqual(self.request.id, self.request_id)
        self.assertEqual(self.request.origin, self.origin)
        self.assertEqual(self.request.destination, self.destination)
        self.assertEqual(self.request.departure_time, self.departure_time)
        self.assertEqual(self.request.cancel_time, self.cancel_time)
        self.assertEqual(len(self.request.passengers), self.passengers)

    def test_request_create_passengers(self):
        """
        turning a request into passengers of a vehicle
        """

        vehicle = mock_vehicle()
        request_as_passengers = self.request.passengers
        updated_vehicle = vehicle.add_passengers(request_as_passengers)

        # should now have 2 passengers
        self.assertEqual(len(updated_vehicle.passengers), 2)

        # the passengers should match our request and have unique names
        for i in range(0, 2):
            # the passengers should have the correct ids
            target_passenger_id = create_passenger_id(self.request_id, i)
            passenger = updated_vehicle.passengers[target_passenger_id]
            self.assertEqual(passenger.id, target_passenger_id)

            # passenger details should be consistent with request
            self.assertEqual(passenger.origin, self.request.origin)
            self.assertEqual(passenger.destination, self.request.destination)
            self.assertEqual(passenger.departure_time, self.request.departure_time)

            # the current vehicle should be known to each passenger
            self.assertEqual(passenger.vehicle_id, vehicle.id)

    def test_from_row(self):
        source = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        """
        row = next(DictReader(source.split()))
        env = mock_env()
        req = Request.from_row(row, env)
        self.assertEqual(req.id, "1_a")
        self.assertEqual(req.origin, h3.geo_to_h3(31.2074449, 121.4294263, env.config.sim.sim_h3_resolution))
        self.assertEqual(req.destination, h3.geo_to_h3(31.2109091, 121.4532226, env.config.sim.sim_h3_resolution))
        self.assertEqual(req.departure_time, 61200)
        self.assertEqual(req.cancel_time, 61800)
        self.assertEqual(len(req.passengers), 4)

    def test_from_row_datetime_good(self):
        row = {
            'request_id': '1_a',
            'o_lat': '0',
            'o_lon': '0',
            'd_lat': '0',
            'd_lon': '0',
            'departure_time': '2019-01-09 11:11:11',
            'cancel_time': '2019-01-09 16:11:11',
            'passengers': '4'
        }
        config = mock_config(parse_dates=True, date_format="%Y-%m-%d %H:%M:%S")
        env = mock_env(config)
        req = Request.from_row(row, env)
        self.assertEqual(req.departure_time, 1547057471)

    def test_from_row_datetime_bad(self):
        row = {
            'request_id': '1_a',
            'o_lat': '0',
            'o_lon': '0',
            'd_lat': '0',
            'd_lon': '0',
            'departure_time': '01-09-2019 11:11:11',
            'cancel_time': '2019-01-09 16:11:11',
            'passengers': '4'
        }
        config = mock_config(parse_dates=True, date_format="%Y-%m-%d %H:%M:%S")
        env = mock_env(config)
        with self.assertRaises(IOError):
            Request.from_row(row, env)




if __name__ == '__main__':
    unittest.main()
