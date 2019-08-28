import os
import sys
import unittest

from build_test_env import setup_env

sys.path.append('../')
from hive.dispatcher import Dispatcher

class DispatcherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.SIM_ENV = setup_env()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_find_closest_plug(self):
        dispatcher = self.SIM_ENV['dispatcher']
        test_vehicle = self.SIM_ENV['fleet'][0]
        test_station = self.SIM_ENV['stations'][0]

        test_vehicle.x = test_station.X
        test_vehicle.y = test_station.Y

        nearest_station = dispatcher._find_closest_plug(test_vehicle, type='station')
        self.assertEqual(test_station.ID, nearest_station.ID)

    def test_get_n_best_vehicles(self):
        dispatcher = self.SIM_ENV['dispatcher']
        test_vehicle = self.SIM_ENV['fleet'][0]
        test_request = self.SIM_ENV['requests'].iloc[0]

        #Make test vehicle the best vehicle
        test_vehicle.x = test_request.pickup_x
        test_vehicle.y = test_request.pickup_y
        test_vehicle.available = True
        test_vehicle.energy_kwh = test_vehicle.BATTERY_CAPACITY
        test_vehicle.avail_seats = test_vehicle.MAX_PASSENGERS

        best_vehicle_id = dispatcher._get_n_best_vehicles(test_request, n=1)[0]
        self.assertEqual(test_vehicle.ID, best_vehicle_id)

        test_vehicle.available = False

        best_vehicle_id = dispatcher._get_n_best_vehicles(test_request, n=1)[0]
        self.assertNotEqual(test_vehicle.ID, best_vehicle_id)

        test_vehicle.available = True
        test_vehicle.energy_kwh = test_vehicle.BATTERY_CAPACITY * self.SIM_ENV['env_params']['MIN_ALLOWED_SOC']

        best_vehicle_id = dispatcher._get_n_best_vehicles(test_request, n=1)[0]
        self.assertNotEqual(test_vehicle.ID, best_vehicle_id)





if __name__ == "__main__":
    unittest.main()
