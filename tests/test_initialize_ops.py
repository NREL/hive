from unittest import TestCase
from pkg_resources import resource_filename

from hive.initialization.initialize_ops import process_fleet_file


class TestIntializeOps(TestCase):

    def test_process_fleet_file(self):
        fleets_file_location = resource_filename("hive.resources.scenarios.denver_downtown.fleets", "denver_duel_fleets.yaml")

        veh_member_ids = process_fleet_file(fleets_file_location, 'vehicles')
        base_member_ids = process_fleet_file(fleets_file_location, 'bases')
        station_member_ids = process_fleet_file(fleets_file_location, 'stations')

        self.assertEqual(veh_member_ids['v7'], ('uber', 'lyft'),
                         "v7 should be a member of both uber and lyft")
        self.assertEqual(veh_member_ids['v1'], ('uber',),
                         "v2 should be a member of uber")
        self.assertEqual(veh_member_ids['v13'], ('lyft',),
                         "v3 should be a member of lyft")

        self.assertEqual(base_member_ids['b1'], ('uber', 'lyft'),
                         "b1 should be a member of both uber and lyft")

        self.assertEqual(station_member_ids['s1'], ('uber', 'lyft'),
                         "s1 should be a member of both uber and lyft")
        self.assertEqual(station_member_ids['s2'], ('uber', 'lyft'),
                         "s2 should be a member of both uber and lyft")
        self.assertEqual(station_member_ids['bs1'], ('uber', 'lyft'),
                         "bs1 should be a member of both uber and lyft")
