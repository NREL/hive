import unittest
import os
import shutil
import pandas as pd

from hive import initialize as init
from hive.dispatcher import Dispatcher

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_INPUT_DIR = os.path.join('inputs', '.inputs_default')
TEST_OUTPUT_DIR = os.path.join(THIS_DIR, '.tmp')

class DispatcherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)

        CHARGE_NET_FILE = os.path.join(TEST_INPUT_DIR,
                                        'charge_network',
                                        'aus_fuel_stations.csv')
        CHARGE_CURVE_FILE = os.path.join(TEST_INPUT_DIR,
                                            '.lib',
                                            'raw_leaf_curves.csv')
        WHMI_LOOKUP_FILE = os.path.join(TEST_INPUT_DIR,
                                            '.lib',
                                            'wh_mi_lookup.csv')
        FLEET_FILE = os.path.join(TEST_INPUT_DIR,
                                            'fleets',
                                            'aus_fleet.csv')

        log_file = os.path.join(TEST_OUTPUT_DIR, 'placeholder.csv')
        fleet_df = pd.read_csv(FLEET_FILE)
        charge_net_df = pd.read_csv(CHARGE_NET_FILE)
        stations, bases = init.initialize_charge_network(charge_net_df,
                                            station_log_file=log_file)
        charge_curve_df = pd.read_csv(CHARGE_CURVE_FILE)
        whmi_df = pd.read_csv(WHMI_LOOKUP_FILE)
        vehicles = list()
        for i, veh in fleet_df.iloc[0:5].iterrows():
            veh_file = os.path.join(TEST_INPUT_DIR, 'vehicles', '{}.csv'.format(veh.VEHICLE_NAME))
            veh_df = pd.read_csv(veh_file)
            veh_df['VEHICLE_NAME'] = veh.VEHICLE_NAME
            veh_df['NUM_VEHICLES'] = veh.NUM_VEHICLES
            vehicles.append(veh_df.iloc[0])
        env_params = {
            'MAX_DISPATCH_MILES': 5,
            'MIN_ALLOWED_SOC': 20,
            'RN_SCALING_FACTOR': 2,
            'DISPATCH_MPH': 30,
        }

        cls.bases = bases
        cls.stations = stations
        cls.fleet = init.initialize_fleet(vehicles,
                                            bases,
                                            charge_curve_df,
                                            whmi_df,
                                            env_params,
                                            vehicle_log_file=log_file)


    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dispatcher(self):
        dispatcher = Dispatcher(fleet = self.fleet,
                                stations = self.stations,
                                bases = self.bases)
        self.assertEqual(1,0)
        #TODO: Develop unit tests for internal Dispatcher functions.
