from typing import Tuple
from unittest import TestCase

from hive.config import *
from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from hive.dispatcher.instruction import Instruction
from hive.model.base import Base
from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powercurve import build_powercurve
from hive.model.energy.powertrain import build_powertrain
from hive.model.request import Request
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.runner.environment import Environment
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.state.simulation_state import SimulationState
from hive.state.simulation_state_ops import initial_simulation_state
from hive.state.update import UpdateRequestsFromString
from hive.state.update.cancel_requests import CancelRequests
from hive.util.units import unit
from hive.reporting.detailed_reporter import DetailedReporter

from h3 import h3


class TestLocalSimulationRunner(TestCase):

    def test_run(self):
        runner = TestLocalSimulationRunnerAssets.mock_runner()
        initial_sim = TestLocalSimulationRunnerAssets.mock_initial_sim()
        req = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1,-37.001,122,-37.1,122,0,20,2
        """
        req_destination = h3.geo_to_h3(-37.1, 122, initial_sim.sim_h3_resolution)
        update_requests = UpdateRequestsFromString(req)

        result = runner.run(
            initial_simulation_state=initial_sim,
            initial_dispatcher=GreedyDispatcher(),
            update_functions=(CancelRequests(), update_requests),
            reporter=DetailedReporter(runner.env.config.io)
        )

        at_destination = result.s.at_geoid(req_destination)
        self.assertIn('1', at_destination['vehicles'], "vehicle should have driven request to destination")

        self.assertAlmostEqual(11.1 * unit.kilometer, result.s.vehicles['1'].distance_traveled, places=1)


class TestLocalSimulationRunnerAssets:

    @classmethod
    def report_nothing(cls, x, y):
        pass

    @classmethod
    def report(cls, sim: SimulationState, instructions: Tuple[Instruction, ...]):
        if len(instructions) > 0:
            print(instructions)
        # print(f"time: {sim.sim_time}")
        print(f"our vehicle: {sim.vehicles['1']} dist {sim.vehicles['1'].distance_traveled}")
        # # print(f"our request: {sim.requests['1']}")
        # print(f"instructions:")
        # print(instructions)

    # todo: replace this stuff with loading a pre-built toy scenario from hive.resources

    @classmethod
    def mock_initial_sim(cls) -> SimulationState:
        sim, errors = initial_simulation_state(
            road_network=HaversineRoadNetwork(),
            vehicles=(cls.mock_vehicle(),),
            stations=(cls.mock_station(),),
            bases=(cls.mock_base(),),
            powertrains=(build_powertrain('leaf'),),
            powercurves=(build_powercurve('leaf'),)
        )
        return sim

    @classmethod
    def mock_vehicle(cls,
                     v_id: str = "1",
                     geoid: str = h3.geo_to_h3(-37, 122, 15)) -> Vehicle:
        return Vehicle(
            id=v_id,
            powertrain_id="leaf",
            powercurve_id="leaf",
            energy_source=EnergySource.build("1",
                                             EnergyType.ELECTRIC,
                                             100 * unit.kilowatthours,
                                             None,
                                             50 * unit.kilowatt
                                             ),
            geoid=geoid,
            property_link=HaversineRoadNetwork().property_link_from_geoid(geoid)
        )

    @classmethod
    def mock_station(cls) -> Station:
        return Station.build("1", h3.geo_to_h3(-36.999, 122, 15), {Charger.DCFC: 1})

    @classmethod
    def mock_base(cls) -> Base:
        return Base.build("1", h3.geo_to_h3(-37, 121.999, 15), None, 5)

    @classmethod
    def mock_runner(cls) -> LocalSimulationRunner:
        return LocalSimulationRunner(
            env=Environment(
                config=TestLocalSimulationRunnerAssets.mock_config()
            )
        )

    @classmethod
    def mock_config(cls) -> HiveConfig:
        return HiveConfig.build({"sim": {'end_time_seconds': 1000},
                                 "io": {'vehicles_file': '', 'requests_file': ''}})
