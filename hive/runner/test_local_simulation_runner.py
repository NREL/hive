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

from h3 import h3


class TestLocalSimulationRunner(TestCase):

    def test_run(self):
        runner = TestLocalSimulationRunnerAssets.mock_runner()
        initial_sim = TestLocalSimulationRunnerAssets.mock_initial_sim()
        initial_sim_with_req = initial_sim.add_request(TestLocalSimulationRunnerAssets.mock_request())
        runner.run(
            initial_simulation_state=initial_sim_with_req,
            initial_dispatcher=GreedyDispatcher(),
            report_state=TestLocalSimulationRunnerAssets.report
        )


class TestLocalSimulationRunnerAssets:

    # todo: replace this stuff with loading a pre-built toy scenario from hive.resources

    @classmethod
    def report(cls, sim: SimulationState, instructions: Tuple[Instruction, ...]):
        print(f"time: {sim.sim_time}")
        print(f"our vehicle: {sim.vehicles['1']}")
        # print(f"our request: {sim.requests['1']}")
        print(f"instructions:")
        print(instructions)

    @classmethod
    def mock_request(cls) -> Request:
        return Request.build(request_id="1",
                             origin=h3.geo_to_h3(-37.001, 122, 15),
                             destination=h3.geo_to_h3(-37.1, 122, 15),
                             departure_time=0,
                             cancel_time=8,
                             passengers=2
                             )

    @classmethod
    def mock_initial_sim(cls) -> SimulationState:
        sim, errors = initial_simulation_state(
            road_network=HaversineRoadNetwork(),
            vehicles=(cls.mock_vehicle(),),
            stations=(cls.mock_station(),),
            bases=(cls.mock_base(),),
            powertrains=(build_powertrain('leaf'), ),
            powercurves=(build_powercurve('leaf'), )
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
            energy_source=EnergySource("1", EnergyType.ELECTRIC, 50, 100, 50),
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
        return HiveConfig.build({"sim": {'end_time_seconds': 100}})
