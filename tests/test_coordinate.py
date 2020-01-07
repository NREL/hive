import unittest
from hive.model.coordinate import Coordinate, dist_euclidian


class MyTestCase(unittest.TestCase):
    def test_coordinate_constructor(self):
        lat, lon = (39.7440165, -105.1591066)
        nrel = Coordinate(lat=lat, lon=lon)
        self.assertEqual(nrel.lat, lat)
        self.assertEqual(nrel.lon, lon)
        self.assertTrue(type(nrel.lat) is float)
        self.assertTrue(type(nrel.lon) is float)

    def test_euclidian_dist(self):
        a, b = (Coordinate(lat=0, lon=0), Coordinate(lat=3, lon=4))
        dist = dist_euclidian(a, b)
        self.assertAlmostEqual(dist, 5.0, 10, "the hypotenuse should be 5 when the other two edges are 3 and 4")


if __name__ == '__main__':
    unittest.main()
