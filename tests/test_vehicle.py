import os
import sys
import unittest
import math

from build_test_env import setup_env

sys.path.append('../')
from hive.vehicle import Vehicle
from hive import units

class VehicleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.SIM_ENV = setup_env()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_vehicle_cmd_make_trip(self):
        test_request = self.SIM_ENV['requests'].iloc[0]
        test_vehicle = self.SIM_ENV['fleet'][0]
        test_vehicle.cmd_make_trip(
                            origin_x = test_request.pickup_x,
                            origin_y = test_request.pickup_y,
                            destination_x = test_request.dropoff_x,
                            destination_y = test_request.dropoff_y,
                            passengers = test_request.passengers,
                            trip_dist_mi = test_request.distance_miles,
                            trip_time_s = test_request.seconds,
                            )
        disp_dist_mi = math.hypot(test_request.dropoff_x - test_vehicle.x, test_request.dropoff_y - test_vehicle.y)\
                * units.METERS_TO_MILES * self.SIM_ENV['env_params']['RN_SCALING_FACTOR']
        disp_time_s = (disp_dist_mi / self.SIM_ENV['env_params']['DISPATCH_MPH']) * units.HOURS_TO_SECONDS

        sim_steps = math.ceil((test_request.seconds + disp_time_s)/self.SIM_ENV['sim_clock'].TIMESTEP_S)
        for t in range(sim_steps):
            test_vehicle.step()
            next(self.SIM_ENV['sim_clock'])

        self.assertTrue(test_vehicle.x == test_request.dropoff_x)
        self.assertTrue(test_vehicle.y == test_request.dropoff_y)
        self.assertTrue(test_vehicle._route == None)
        self.assertTrue(test_vehicle.activity == 'Idle')

    def test_vehicle_cmd_travel_to(self):
        test_request = self.SIM_ENV['requests'].iloc[1]
        test_vehicle = self.SIM_ENV['fleet'][1]

        test_vehicle.cmd_travel_to(
                            destination_x = test_request.pickup_x,
                            destination_y = test_request.pickup_y,
                            )

        disp_dist_mi = math.hypot(test_request.pickup_x - test_vehicle.x, test_request.pickup_y - test_vehicle.y)\
                * units.METERS_TO_MILES * self.SIM_ENV['env_params']['RN_SCALING_FACTOR']
        disp_time_s = (disp_dist_mi / self.SIM_ENV['env_params']['DISPATCH_MPH']) * units.HOURS_TO_SECONDS

        sim_steps = math.ceil(disp_time_s/self.SIM_ENV['sim_clock'].TIMESTEP_S)
        for t in range(sim_steps):
            test_vehicle.step()

        self.assertTrue(test_vehicle.x == test_request.pickup_x)
        self.assertTrue(test_vehicle.y == test_request.pickup_y)
        self.assertTrue(test_vehicle._route == None)

    def test_vehicle_cmd_charge(self):
        test_vehicle = self.SIM_ENV['fleet'][0]
        test_station = self.SIM_ENV['stations'][0]

        pre_avail_plugs = test_station.avail_plugs

        test_vehicle.cmd_charge(test_station)

        disp_dist_mi = math.hypot(test_station.X - test_vehicle.x, test_station.Y - test_vehicle.y)\
                * units.METERS_TO_MILES * self.SIM_ENV['env_params']['RN_SCALING_FACTOR']
        disp_time_s = (disp_dist_mi / self.SIM_ENV['env_params']['DISPATCH_MPH']) * units.HOURS_TO_SECONDS

        sim_steps = math.ceil(disp_time_s/self.SIM_ENV['sim_clock'].TIMESTEP_S)

        for t in range(sim_steps):
            test_vehicle.step()

        self.assertTrue(test_vehicle.x == test_station.X)
        self.assertTrue(test_vehicle.y == test_station.Y)
        self.assertTrue(test_vehicle._station == test_station)
        self.assertTrue(test_station.avail_plugs == pre_avail_plugs - 1)

        test_vehicle.energy_kwh = test_vehicle.BATTERY_CAPACITY * 0.5

        max_s = test_vehicle.BATTERY_CAPACITY / test_station.PLUG_POWER_KW * units.HOURS_TO_SECONDS
        max_iter = max_s / self.SIM_ENV['sim_clock'].TIMESTEP_S

        i = 0
        while test_vehicle.activity == 'Charging at Station':
            i += 1
            if i > max_iter:
                raise RuntimeError("Vehicle charging too long")
            test_vehicle.step()

        self.assertTrue(test_vehicle.soc > self.SIM_ENV['env_params']['UPPER_SOC_THRESH_STATION'] - 0.1)
        self.assertTrue(test_vehicle.soc < self.SIM_ENV['env_params']['UPPER_SOC_THRESH_STATION'])
        self.assertTrue(test_station.avail_plugs == pre_avail_plugs)





if __name__ == "__main__":
    unittest.main()
