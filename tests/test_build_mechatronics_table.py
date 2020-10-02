from unittest import TestCase

from hive.model.vehicle.mechatronics.__init__ import build_mechatronics_table
from tests.mock_lobster import *

def setupMockInput(scenario_directory: str, mechatronics_file: str) -> Input:
    mock = mock_input(
        scenario_directory=scenario_directory,  # loaded from command line
        scenario_file='scenario_file',  # loaded from command line as well
        vehicles_file='vehicles_file',
        requests_file='requests_file',
        bases_file='bases_file',
        stations_file='stations_file',
        mechatronics_file=mechatronics_file,
        chargers_file='chargers_file',
        road_network_file='road_network_file',
        geofence_file='geofence_file',
        rate_structure_file='rate_structure_file',
        charging_price_file='charging_price_file',
        demand_forecast_file='demand_forecast_file', )
    return mock


class TestBuildMechatronicsTable(TestCase):

    def testBuildValidTable(self):
        input = setupMockInput('hive\hive\resources\scenarios\denver_downtown', 'test_assets/mock_mechatronics.yaml')
        try:
            build_mechatronics_table(input)
        except KeyError:
            self.fail("build_mechatronics_table threw KeyError unexpectedly!")

    def testBuildInvalidTable(self):
        input = setupMockInput('hive\hive\resources\scenarios\denver_downtown', 'test_assets/mock_bad_mechatronics.yaml')
        self.assertRaises(IOError, build_mechatronics_table, input)

    def testMissingFile(self):
        input = setupMockInput('test_assets/', 'test_assets/not_real_mechatronics.yaml')
        self.assertRaises(FileNotFoundError, build_mechatronics_table, input)
