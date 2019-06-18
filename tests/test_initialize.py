import os
import sys
import unittest
import shutil
import pandas as pd

sys.path.append('../')
from hive.initialize import initialize_stations, initialize_bases, initialize_fleet
from hive.stations import FuelStation, VehicleBase
from hive.vehicle import Vehicle

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_INPUT_DIR = os.path.join('../', 'inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join(THIS_DIR, '.tmp')

class InitializeChargeNetworkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)

        cls.CHARGE_STATIONS_FILE = os.path.join(TEST_INPUT_DIR,
                                                'charge_network',
                                                'aus_fuel_stations.csv')

        cls.VEHICLE_BASES_FILE = os.path.join(TEST_INPUT_DIR,
                                              'charge_network',
                                              'aus_veh_bases.csv')

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_charging_network_stations(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        stations_df = pd.read_csv(self.CHARGE_STATIONS_FILE)
        stations = initialize_stations(stations_df,
                                       station_log_file=log_file)
        self.assertEqual(len(stations), 186)
        self.assertIsInstance(stations[0], FuelStation)
        self.assertEqual(stations[0]._logfile, log_file)

    def test_initialize_charging_network_bases(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        bases_df = pd.read_csv(self.VEHICLE_BASES_FILE)
        bases, _ = initialize_bases(bases_df,
                                 base_log_file=log_file)
        self.assertEqual(len(bases), 2)
        self.assertIsInstance(bases[0], VehicleBase)
        self.assertEqual(bases[0]._logfile, log_file)

    def test_initialize_base_power_dict(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        bases_df = pd.read_csv(self.VEHICLE_BASES_FILE)
        _, base_power_dict = initialize_bases(bases_df,
                                              base_log_file=log_file)
        self.assertEqual(len(base_power_dict.keys()), 2)
        self.assertTrue('type' in base_power_dict['b1'].keys())
        self.assertTrue('kw' in base_power_dict['b1'].keys())

class InitializeFleetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)

        cls.VEHICLE_BASES_FILE = os.path.join(TEST_INPUT_DIR,
                                              'charge_network',
                                              'aus_veh_bases.csv')
        cls.CHARGE_CURVE_FILE = os.path.join(TEST_INPUT_DIR,
                                            '.lib',
                                            'raw_leaf_curves.csv')
        cls.WHMI_LOOKUP_FILE = os.path.join(TEST_INPUT_DIR,
                                            '.lib',
                                            'wh_mi_lookup.csv')
        cls.FLEET_FILE = os.path.join(TEST_INPUT_DIR,
                                            'fleets',
                                            'aus_fleet.csv')


    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)


    def setUp(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        fleet_df = pd.read_csv(self.FLEET_FILE)
        bases_df = pd.read_csv(self.VEHICLE_BASES_FILE)
        bases, _ = initialize_bases(bases_df,
                                 base_log_file=log_file)
        self.bases = bases
        self.charge_curve_df = pd.read_csv(self.CHARGE_CURVE_FILE)
        self.whmi_df = pd.read_csv(self.WHMI_LOOKUP_FILE)
        self.vehicles = list()
        for _, veh in fleet_df.iterrows():
            veh_file = os.path.join(TEST_INPUT_DIR, 'vehicles', '{}.csv'.format(veh.VEHICLE_NAME))
            veh_df = pd.read_csv(veh_file)
            veh_df['VEHICLE_NAME'] = veh.VEHICLE_NAME
            veh_df['NUM_VEHICLES'] = veh.NUM_VEHICLES
            self.vehicles.append(veh_df.iloc[0])
        self.env_params = {
            'MAX_DISPATCH_MILES': 5,
            'MIN_ALLOWED_SOC': 20,
            'RN_SCALING_FACTOR': 2,
            'DISPATCH_MPH': 30,
        }

    def tearDown(self):
        pass

    def test_initialize_fleet_size(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        summary_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        fleet = initialize_fleet(self.vehicles,
                                    self.bases,
                                    self.charge_curve_df,
                                    self.whmi_df,
                                    self.env_params,
                                    vehicle_log_file = log_file,
                                    vehicle_summary_file = summary_file)

        self.assertEqual(len(fleet), 130)

    def test_initialize_fleet_type(self):
        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        fleet = initialize_fleet(self.vehicles[0:1],
                                    self.bases,
                                    self.charge_curve_df,
                                    self.whmi_df,
                                    self.env_params,
                                    vehicle_log_file = log_file,
                                    vehicle_summary_file = summary_file)
        self.assertIsInstance(fleet[0], Vehicle)

if __name__ == '__main__':
    unittest.main()
