from unittest import TestCase

from hive.initialization.initialize_ops import process_fleet_file


class TestIntializeOps(TestCase):

    def test_process_fleet_file(self):
        veh_member_ids = process_fleet_file('test_assets/fleet_valid.yaml', 'vehicles')
        base_member_ids = process_fleet_file('test_assets/fleet_valid.yaml', 'bases')
        station_member_ids = process_fleet_file('test_assets/fleet_valid.yaml', 'stations')

        print(veh_member_ids)

        self.assertEqual(veh_member_ids['v1'], ('test_fleet_1', 'test_fleet_2'),
                         "v1 should be a member of both test_fleet_1 and test_fleet_2")
        self.assertEqual(veh_member_ids['v2'], ('test_fleet_1',),
                         "v2 should be a member of test_fleet_1")
        self.assertEqual(veh_member_ids['v3'], ('test_fleet_2',),
                         "v3 should be a member of test_fleet_2")

        self.assertEqual(base_member_ids['b1'], ('test_fleet_1', 'test_fleet_2'),
                         "b1 should be a member of both test_fleet_1 and test_fleet_2")
        self.assertEqual(base_member_ids['b2'], ('test_fleet_1',),
                         "b2 should be a member of test_fleet_1")
        self.assertEqual(base_member_ids['b3'], ('test_fleet_2',),
                         "b3 should be a member of test_fleet_2")

        self.assertEqual(station_member_ids['s1'], ('test_fleet_1', 'test_fleet_2'),
                         "s1 should be a member of both test_fleet_1 and test_fleet_2")
        self.assertEqual(station_member_ids['s2'], ('test_fleet_1',),
                         "s2 should be a member of test_fleet_1")
        self.assertEqual(station_member_ids['bs1'], ('test_fleet_2',),
                         "bs1 should be a member of test_fleet_2")
