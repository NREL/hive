from unittest import TestCase

from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from hive.state.update import UpdateRequestsFromString
from hive.state.update.cancel_requests import CancelRequests
from tests.mock_lobster import *


class TestLocalSimulationRunner(TestCase):

    def test_run(self):
        runner = mock_runner(mock_config(end_time_seconds=20, timestep_duration_seconds=1))
        initial_sim = mock_sim(
            vehicles=(mock_vehicle(lat=-37, lon=122, capacity=100 * unit.kilowatthours, ideal_energy_limit=None),),
            stations=(mock_station(lat=-36.999, lon=122),),
            bases=(mock_base(stall_count=5, lat=-37, lon=121.999),),
        )
        req = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1,-37.001,122,-37.1,122,0,3600,2
        """
        req_destination = h3.geo_to_h3(-37.1, 122, initial_sim.sim_h3_location_resolution)
        update_requests = UpdateRequestsFromString.build(req)

        result = runner.run(
            initial_simulation_state=initial_sim,
            initial_dispatcher=GreedyDispatcher(),
            update_functions=(CancelRequests(), update_requests),
            reporter=mock_reporter()
        )

        at_destination = result.s.at_geoid(req_destination)
        self.assertIn(DefaultIds.mock_vehicle_id(), at_destination['vehicles'],
                      "vehicle should have driven request to destination")

        self.assertAlmostEqual(11.1 * unit.kilometer, result.s.vehicles[DefaultIds.mock_vehicle_id()].distance_traveled, places=1)

