from unittest import TestCase, skip

from pkg_resources import resource_string

from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.state.simulation_state import SimulationState
from hive.state.simulation_state_ops import initial_simulation_state
from hive.state.update.update_requests_from_file import UpdateRequestsFromFile


class TestUpdateRequestsFromFile(TestCase):
    @skip("can't track file position (file.tell()) and iterate (next(dict_reader)): https://stackoverflow.com/questions/29618936/how-to-solve-oserror-telling-position-disabled-by-next-call")
    def test_update(self):
        """
        test invariant: a file exists at asdf.asdf.asdf.foo.csv
        """
        sim = TestUpdateRequestsFromFileAssets.mock_sim()
        # req_file = resource_string('hive.resources.scenarios.test_scenario', 'requests.csv')
        req_file = "/Users/rfitzger/dev/nrel/hive/hive/hive/resources/scenarios/test_scenario/requests.csv"
        fn = UpdateRequestsFromFile(req_file)
        result = fn.update(sim)
        self.assertEqual(len(result.reports), 1, "should have reported the add")
        self.assertEqual(len(result.simulation_state.requests), 1, "should have added the req")


class TestUpdateRequestsFromFileAssets:

    @classmethod
    def mock_sim(cls, start_time=61200) -> SimulationState:
        sim, errors = initial_simulation_state(HaversineRoadNetwork(), start_time=start_time)
        return sim
