from unittest import TestCase

from nrel.hive.resources.mock_lobster import *


class TestKeplerFeature(TestCase):
    def test_add_coord(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)

        self.assertIn(
            (somewhere(), mock_sim().sim_time),
            feature.coords,
            "Coordinates were not added to the list of coords",
        )
        self.assertEquals(1, len(feature.coords), "There should only be one coord in coords")

    def test_gen_json(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)
        feature.add_coord(somewhere_else(), mock_sim().sim_time + 1)

        actual_dict = feature.gen_json()
        expected_dict = {
            "type": "Feature",
            "properties": {
                "vehicle_id": DefaultIds.mock_vehicle_id(),
                "vehicle_state": "Idle",
                "start_time": f"{mock_sim().sim_time.as_epoch_time():010}",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [
                        h3.h3_to_geo(somewhere())[1],
                        h3.h3_to_geo(somewhere())[0],
                        0,
                        f"{mock_sim().sim_time.as_epoch_time():010}",
                    ],
                    [
                        h3.h3_to_geo(somewhere_else())[1],
                        h3.h3_to_geo(somewhere_else())[0],
                        0,
                        f"{(mock_sim().sim_time + 1).as_epoch_time():010}",
                    ],
                ],
            },
        }

        self.assertDictEqual(expected_dict, actual_dict)

    def test_reset(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)
        feature.add_coord(somewhere_else(), mock_sim().sim_time + 1)

        feature.reset("DispatchTrip", mock_sim().sim_time + 2)

        self.assertEquals(0, len(feature.coords), "Reset did not delete the old coordinates")
        self.assertEquals("DispatchTrip", feature.state, "State did not change in reset")
        self.assertEquals(
            mock_sim().sim_time + 2, feature.starttime, "Start time did not get updated"
        )
        self.assertEquals(DefaultIds.mock_vehicle_id(), feature.id, "ID should not change in reset")
