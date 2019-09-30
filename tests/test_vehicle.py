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
        cls.test_route = [
                 ((30.202783, -97.666996), 0.07102958574108299, 'Dispatch to Request'),
                 ((30.208332, -97.662686), 0.493413042415615, 'Dispatch to Request'),
                 ((30.213601, -97.66001), 0.5533686206813949, 'Dispatch to Request'),
                 ((30.21996, -97.671558), 0.833339376843311, 'Dispatch to Request'),
                 ((30.224305, -97.680064), 0.5935336394729871, 'Serving Trip'),
                 ((30.232749, -97.683968), 0.630330923757084, 'Serving Trip'),
                 ((30.244267, -97.69055), 0.8694615030109061, 'Serving Trip'),
                 ((30.251038, -97.682555), 0.8056719805472987, 'Serving Trip'),
                 ((30.251642, -97.682966), 0.5294079882310436, 'Serving Trip'),
                 ((30.250266, -97.690443), 0.42695224167341106, 'Serving Trip'),
                 ((30.25596, -97.692917), 0.4757713994751649, 'Serving Trip'),
                 ((30.26561, -97.695509), 0.7007186438184752, 'Serving Trip'),
                 ((30.275509, -97.699186), 0.694840492799603, 'Serving Trip'),
                 ((30.283419, -97.70453), 0.6628251622923864, 'Serving Trip'),
                 ((30.291561, -97.707424), 0.5641935018816682, 'Serving Trip'),
                 ((30.300444, -97.712642), 0.7402605716551385, 'Serving Trip'),
                 ((30.30841, -97.71562), 0.6912386337771323, 'Serving Trip'),
                 ((30.318853, -97.712776), 0.7062616633594612, 'Serving Trip'),
                 ((30.321547, -97.717621), 0.4580678953234347, 'Serving Trip'),
                 ((30.326714, -97.727055), 0.6993308732057084, 'Serving Trip'),
                 ((30.332404, -97.734766), 0.6373112489855863, 'Serving Trip'),
                 ((30.338078, -97.739318), 0.59537288582694, 'Serving Trip'),
                 ((30.34189, -97.737495), 0.2661897347404363, 'Serving Trip'),
                 ((30.342606, -97.737133), 0.10273534051690625, 'Serving Trip')
                 ]
        cls.test_route_distance = 0
        for step in cls.test_route:
            cls.test_route_distance += step[1]

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_vehicle_cmd_make_trip(self):
        test_vehicle = self.SIM_ENV['fleet'][2]
        test_vehicle.x = self.test_route[0][0][0]
        test_vehicle.y = self.test_route[0][0][1]

        test_vehicle.cmd_make_trip(
                            route = self.test_route,
                            passengers = 1,
                            )

        sim_steps = len(self.test_route)
        for t in range(sim_steps+1):
            test_vehicle.step()

        end_x = self.test_route[-1][0][0]
        end_y = self.test_route[-1][0][1]

        self.assertTrue(test_vehicle.x == end_x)
        self.assertTrue(test_vehicle.y == end_y)
        self.assertTrue(test_vehicle._route == None)
        self.assertTrue(test_vehicle.activity == 'Idle')

    def test_vehicle_cmd_move(self):
        test_vehicle = self.SIM_ENV['fleet'][2]
        test_vehicle.x = self.test_route[0][0][0]
        test_vehicle.y = self.test_route[0][0][1]

        end_x = self.test_route[-1][0][0]
        end_y = self.test_route[-1][0][1]

        test_vehicle.cmd_move(self.test_route)

        sim_steps = len(self.test_route)
        for t in range(sim_steps+1):
            test_vehicle.step()

        self.assertTrue(test_vehicle.x == end_x)
        self.assertTrue(test_vehicle.y == end_y)
        self.assertTrue(test_vehicle._route == None)

    def test_vehicle_cmd_charge(self):
        test_vehicle = self.SIM_ENV['fleet'][2]
        test_station = self.SIM_ENV['stations'][2]

        pre_avail_plugs = test_station.avail_plugs

        router = self.SIM_ENV['dispatcher']._route_engine
        route_summary = router.route(
                        test_vehicle.x,
                        test_vehicle.y,
                        test_station.X,
                        test_station.Y,
                        activity='Moving to Station')

        route = route_summary['route']

        test_vehicle.cmd_charge(test_station, route)

        sim_steps = len(route)

        for t in range(sim_steps+1):
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
        self.assertEqual(test_station.avail_plugs, pre_avail_plugs)

    def test_vehicle_cmd_return_to_base(self):
        test_vehicle = self.SIM_ENV['fleet'][3]
        test_base = self.SIM_ENV['bases'][0]

        pre_avail_plugs = test_base.avail_plugs

        router = self.SIM_ENV['dispatcher']._route_engine
        route_summary = router.route(
                            test_vehicle.x,
                            test_vehicle.y,
                            test_base.X,
                            test_base.Y,
                            activity = "Returning to Base")

        route = route_summary['route']

        test_vehicle.cmd_return_to_base(test_base, route)

        sim_steps = len(route)

        for t in range(sim_steps+1):
            test_vehicle.step()

        test_vehicle.energy_kwh = test_vehicle.BATTERY_CAPACITY * 0.5
        test_vehicle.step()

        self.assertEqual(test_vehicle.x, test_base.X)
        self.assertEqual(test_vehicle.y, test_base.Y)
        self.assertEqual(test_vehicle._base, test_base)
        self.assertEqual(test_vehicle._station, test_base)
        self.assertEqual(test_base.avail_plugs, pre_avail_plugs - 1)
        self.assertEqual(test_vehicle.activity,  "Charging at Station")





if __name__ == "__main__":
    unittest.main()
