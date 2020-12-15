from unittest import TestCase
from pkg_resources import resource_filename

from hive.initialization.initialize_ops import process_fleet_file


class TestIntializeOps(TestCase):

    def test_process_fleet_file(self):
        fleets_file_location = resource_filename("hive.resources.scenarios.denver_downtown.fleets", "denver_duel_fleets.yaml")

        veh_member_ids = process_fleet_file(fleets_file_location, 'vehicles')
        base_member_ids = process_fleet_file(fleets_file_location, 'bases')
        station_member_ids = process_fleet_file(fleets_file_location, 'stations')

        self.assertEqual(len(veh_member_ids['v7']), 2,
                         "v7 should be a member of two fleets")
        self.assertEqual(len(veh_member_ids['v13']), 1,
                         "v3 should be a member of only one fleet")

        self.assertEqual(len(base_member_ids['b1']), 1,
                         "b1 should only be a member of one fleet")

        self.assertEqual(len(station_member_ids['s1']), 1,
                         "s1 should be only be a member of one fleet")
