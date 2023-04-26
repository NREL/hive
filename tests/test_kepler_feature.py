from unittest import TestCase

import h3

from nrel.hive.resources.mock_lobster import DefaultIds, mock_sim, somewhere, somewhere_else
from nrel.hive.reporting.handler.kepler_feature import Coord, Feature, KeplerFeature


class TestKeplerFeature(TestCase):
    def test_add_coord(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)

        self.assertIn(
            (somewhere(), mock_sim().sim_time),
            feature.coords,
            "Coordinates were not added to the list of coords",
        )
        self.assertEqual(1, len(feature.coords), "There should only be one coord in coords")

    def test_gen_json(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)
        feature.add_coord(somewhere_else(), mock_sim().sim_time + 1)

        actual_dict = feature.gen_json()

        # asserts are needed to get the TypeDict for the expected result to be happy
        lat_1, lon_1 = h3.h3_to_geo(somewhere())
        assert isinstance(lat_1, float)
        assert isinstance(lon_1, float)

        lat_2, lon_2 = h3.h3_to_geo(somewhere_else())
        assert isinstance(lat_2, float)
        assert isinstance(lon_2, float)

        expected_dict: Feature = {
            "type": "Feature",
            "properties": {
                "vehicle_id": DefaultIds.mock_vehicle_id(),
                "vehicle_state": "Idle",
                "start_time": mock_sim().sim_time.as_epoch_time(),
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    Coord(
                        lon_1,
                        lat_1,
                        0,
                        mock_sim().sim_time.as_epoch_time(),
                    ),
                    Coord(
                        lon_2,
                        lat_2,
                        0,
                        (mock_sim().sim_time + 1).as_epoch_time(),
                    ),
                ],
            },
        }

        self.assertDictEqual(expected_dict, actual_dict)

    def test_reset(self):
        feature = KeplerFeature(DefaultIds.mock_vehicle_id(), "Idle", mock_sim().sim_time)
        feature.add_coord(somewhere(), mock_sim().sim_time)
        feature.add_coord(somewhere_else(), mock_sim().sim_time + 1)

        feature.reset("DispatchTrip", mock_sim().sim_time + 2)

        self.assertEqual(0, len(feature.coords), "Reset did not delete the old coordinates")
        self.assertEqual("DispatchTrip", feature.state, "State did not change in reset")
        self.assertEqual(
            mock_sim().sim_time + 2, feature.starttime, "Start time did not get updated"
        )
        self.assertEqual(DefaultIds.mock_vehicle_id(), feature.id, "ID should not change in reset")
