from unittest import TestCase
from csv import DictReader

import h3
from nrel.hive.model.request.request import Request
from nrel.hive.model.sim_time import SimTime
from nrel.hive.resources.mock_lobster import mock_config, mock_env, mock_network, mock_request

from nrel.hive.util.exception import TimeParseError


class TestRequest(TestCase):
    request_id = "test"
    origin = h3.geo_to_h3(0, 0, resolution=11)
    destination = h3.geo_to_h3(3, 4, resolution=11)
    departure_time = 28800
    passengers = 2

    request = mock_request(
        request_id=request_id,
        o_lat=0,
        o_lon=0,
        d_lat=3,
        d_lon=4,
        h3_res=11,
        departure_time=SimTime(28800),
        passengers=2,
    )

    def test_request_constructor(self):
        """
        the constructed request should not modify its arguments
        """
        self.assertEqual(self.request.id, self.request_id)
        self.assertEqual(self.request.origin, self.origin)
        self.assertEqual(self.request.destination, self.destination)
        self.assertEqual(self.request.departure_time, self.departure_time)
        self.assertEqual(len(self.request.passengers), self.passengers)

    def test_from_row(self):
        source = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        """
        row = next(DictReader(source.split()))
        env = mock_env()
        network = mock_network()
        _, req = Request.from_row(row, env, network)
        self.assertEqual(req.id, "1_a")
        self.assertEqual(
            req.origin,
            h3.geo_to_h3(31.2074449, 121.4294263, env.config.sim.sim_h3_resolution),
        )
        self.assertEqual(
            req.destination,
            h3.geo_to_h3(31.2109091, 121.4532226, env.config.sim.sim_h3_resolution),
        )
        self.assertEqual(req.departure_time, 61200)
        self.assertEqual(len(req.passengers), 4)
        self.assertTrue(req.membership.public)

    def test_from_row_with_fleet_id(self):
        source = """
        request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers,fleet_id
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4,uber
        """
        row = next(DictReader(source.split()))
        env = mock_env()
        network = mock_network()
        _, req = Request.from_row(row, env, network)
        self.assertEqual(req.id, "1_a")
        self.assertEqual(
            req.origin,
            h3.geo_to_h3(31.2074449, 121.4294263, env.config.sim.sim_h3_resolution),
        )
        self.assertEqual(
            req.destination,
            h3.geo_to_h3(31.2109091, 121.4532226, env.config.sim.sim_h3_resolution),
        )
        self.assertEqual(req.departure_time, 61200)
        self.assertEqual(len(req.passengers), 4)
        self.assertTrue("uber" in req.membership.memberships)

    def test_from_row_datetime_bad(self):
        row = {
            "request_id": "1_a",
            "o_lat": "0",
            "o_lon": "0",
            "d_lat": "0",
            "d_lon": "0",
            "departure_time": "01-09-2019 11:11:11",
            "passengers": "4",
        }
        config = mock_config(
            start_time="2019-01-09T00:00:00",
            end_time="2019-01-10T00:00:00",
        )
        env = mock_env(config)
        network = mock_network()
        error, request = Request.from_row(row, env, network)
        self.assertIsNone(request)
        self.assertIsInstance(error, TimeParseError)
