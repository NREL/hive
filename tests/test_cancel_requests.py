from unittest import TestCase

from hive.model.energy.powercurve import Powercurve, build_powercurve
from hive.model.energy.powertrain import build_powertrain, Powertrain
from hive.model.request import Request
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.state.simulation_state import SimulationState
from hive.state.simulation_state_ops import initial_simulation_state

from h3 import h3

from hive.state.update.cancel_requests import CancelRequests
from hive.util.typealiases import GeoId


class TestCancelRequests(TestCase):
    def test_update_cancellable(self):
        req = TestCancelRequestsAssets.mock_request()
        sim = TestCancelRequestsAssets.mock_sim(start_time=600).add_request(req)
        cancel_requests = CancelRequests()
        result = cancel_requests.update(sim)
        self.assertNotIn(req.id, result.simulation_state.requests, "request should have been removed")
        self.assertNotIn(req.origin, result.simulation_state.r_locations, "request location should have been removed")
        self.assertEqual(len(result.reports), 1, "should have produced a cancellation report")

    def test_update_not_cancellable(self):
        req = TestCancelRequestsAssets.mock_request()
        sim = TestCancelRequestsAssets.mock_sim(start_time=599).add_request(req)
        cancel_requests = CancelRequests()
        result = cancel_requests.update(sim)
        self.assertIn(req.id, result.simulation_state.requests, "request should not have been removed")
        self.assertIn(req.origin, result.simulation_state.r_locations, "request location should not have been removed")


class TestCancelRequestsAssets:

    @classmethod
    def mock_powertrain(cls) -> Powertrain:
        return build_powertrain('leaf')

    @classmethod
    def mock_powercurve(cls) -> Powercurve:
        return build_powercurve('leaf')

    @classmethod
    def mock_sim(cls, start_time: int = 0) -> SimulationState:
        sim, errors = initial_simulation_state(HaversineRoadNetwork(),
                                        powertrains=(cls.mock_powertrain(),),
                                        powercurves=(cls.mock_powercurve(),),
                                        start_time=start_time)
        return sim

    @classmethod
    def mock_request(cls,
                     request_id="r1",
                     origin: GeoId = h3.geo_to_h3(39.74, -105, 15),
                     destination: GeoId = h3.geo_to_h3(39.76, -105, 15),
                     passengers: int = 2) -> Request:
        return Request.build(
            request_id=request_id,
            origin=origin,
            destination=destination,
            departure_time=0,
            cancel_time=600,
            passengers=passengers
        )