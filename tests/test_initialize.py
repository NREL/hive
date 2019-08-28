import sys
import unittest
import datetime

from build_test_env import load_test_scenario

sys.path.append('../')
from hive.initialize import initialize_stations, initialize_fleet
from hive.stations import FuelStation
from hive.vehicle import Vehicle
from hive.constraints import FLEET_STATE_IDX
from hive.utils import Clock


class InitializeChargeNetworkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.DATA = load_test_scenario()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_stations(self):
        stations = initialize_stations(self.DATA['stations'], clock=None)
        self.assertEqual(len(stations), 186)
        self.assertIsInstance(stations[0], FuelStation)

class InitializeFleetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.DATA = load_test_scenario()
        cls.ENV_PARAMS = {'FLEET_STATE_IDX': FLEET_STATE_IDX}

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.bases = initialize_stations(self.DATA['bases'], clock=None)
        self.vehicle_types = [veh for veh in self.DATA['vehicles'].itertuples()]

    def tearDown(self):
        pass

    def test_initialize_fleet_size(self):
        fleet, fleet_state = initialize_fleet(
                                    vehicle_types = self.vehicle_types,
                                    bases = self.bases,
                                    charge_curve = self.DATA['charge_curves'],
                                    whmi_lookup = self.DATA['whmi_lookup'],
                                    start_time = datetime.date.today(),
                                    env_params = self.ENV_PARAMS,
                                    clock = Clock(60),
                                    )

        self.assertEqual(len(fleet), 130)
        self.assertIsInstance(fleet[0], Vehicle)


if __name__ == '__main__':
    unittest.main()
