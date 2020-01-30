from typing import Optional, Dict, NamedTuple, Union
import functools as ft
import math

from h3 import h3

from hive.config import HiveConfig
from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.forecaster.forecast import Forecast, ForecastType
from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.dispatcher.manager.fleet_target import FleetStateTarget, StateTarget
from hive.model import Base, Station, Vehicle
from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powercurve import Powercurve
from hive.model.energy.powertrain import Powertrain
from hive.model.request import Request, RequestRateStructure
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route
from hive.model.vehiclestate import VehicleState
from hive.reporting.reporter import Reporter
from hive.runner.environment import Environment
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.state.simulation_state import SimulationState
from hive.util.typealiases import *
from hive.util.units import KwH, Kw, Ratio, Kmph, Seconds, SECONDS_TO_HOURS, Currency


class DefaultIds:

    @classmethod
    def mock_request_id(cls) -> RequestId:
        return "r0"

    @classmethod
    def mock_vehicle_id(cls) -> VehicleId:
        return "v0"

    @classmethod
    def mock_station_id(cls) -> StationId:
        return "s0"

    @classmethod
    def mock_base_id(cls) -> BaseId:
        return "b0"

    @classmethod
    def mock_powertrain_id(cls) -> PowertrainId:
        return "pt0"

    @classmethod
    def mock_powercurve_id(cls) -> PowercurveId:
        return "pc0"


def mock_network(h3_res: int = 15) -> RoadNetwork:
    return HaversineRoadNetwork(h3_res)


def mock_energy_source(
        powercurve_id: PowercurveId = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        capacity_kwh: KwH = 100,
        max_charge_acceptance_kw: Kw = 50.0,
        ideal_energy_limit_kwh: KwH = 50.0,
        soc: Ratio = 0.25,
) -> EnergySource:
    return EnergySource.build(
        powercurve_id=powercurve_id,
        energy_type=energy_type,
        capacity_kwh=capacity_kwh,
        ideal_energy_limit_kwh=ideal_energy_limit_kwh,
        max_charge_acceptance_kw=max_charge_acceptance_kw,
        soc=soc)


def mock_base(
        base_id: BaseId = DefaultIds.mock_base_id(),
        lat: float = 0,
        lon: float = 0,
        h3_res: int = 15,
        station_id: Optional[StationId] = None,
        stall_count: int = 1
) -> Base:
    return Base.build(base_id,
                      h3.geo_to_h3(lat, lon, h3_res),
                      station_id,
                      stall_count,
                      )


def mock_base_from_geoid(
        base_id: BaseId = DefaultIds.mock_base_id(),
        geoid: GeoId = h3.geo_to_h3(0, 0, 15),
        station_id: Optional[StationId] = None,
        stall_count: int = 1
) -> Base:
    return Base.build(base_id, geoid, station_id, stall_count)


def mock_station(
        station_id: StationId = DefaultIds.mock_station_id(),
        lat: float = 0,
        lon: float = 0,
        h3_res: int = 15,
        chargers=None
) -> Station:
    if chargers is None:
        chargers = {Charger.LEVEL_2: 1, Charger.DCFC: 1}
    return Station.build(station_id, h3.geo_to_h3(lat, lon, h3_res), chargers)


def mock_station_from_geoid(
        station_id: StationId = DefaultIds.mock_station_id(),
        geoid: GeoId = h3.geo_to_h3(0, 0, 15),
        chargers=None
) -> Station:
    if chargers is None:
        chargers = {Charger.LEVEL_2: 1, Charger.DCFC: 1}
    return Station.build(station_id, geoid, chargers)

def mock_rate_structure(
        base_price: Currency = 2.2,
        price_per_mile: Currency = 1.6,
        minimum_price: Currency = 5
) -> RequestRateStructure:
    return RequestRateStructure(
        base_price=base_price,
        price_per_mile=price_per_mile,
        minimum_price=minimum_price,
    )

def mock_request(
        request_id: RequestId = DefaultIds.mock_request_id(),
        o_lat: float = 0,
        o_lon: float = 0,
        d_lat: float = 10,
        d_lon: float = 10,
        h3_res: int = 15,
        departure_time: SimTime = 0,
        cancel_time: SimTime = 5,
        passengers: int = 1
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=h3.geo_to_h3(o_lat, o_lon, h3_res),
        destination=h3.geo_to_h3(d_lat, d_lon, h3_res),
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers
    )


def mock_request_from_geoids(
        request_id: RequestId = DefaultIds.mock_request_id(),
        origin: GeoId = h3.geo_to_h3(0, 0, 15),
        destination: GeoId = h3.geo_to_h3(10, 10, 15),
        departure_time: SimTime = 0,
        cancel_time: SimTime = 5,
        passengers: int = 1
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers
    )


def mock_vehicle(
        vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
        lat: float = 0,
        lon: float = 0,
        h3_res: int = 15,
        powertrain_id: str = DefaultIds.mock_powertrain_id(),
        powercurve_id: str = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        capacity_kwh: KwH = 100,
        soc: Ratio = 0.25,
        ideal_energy_limit_kwh=50.0,
        max_charge_acceptance_kw: Kw = 50.0,

) -> Vehicle:
    road_network = mock_network(h3_res)
    energy_source = mock_energy_source(
        powercurve_id=powercurve_id,
        energy_type=energy_type,
        capacity_kwh=capacity_kwh,
        ideal_energy_limit_kwh=ideal_energy_limit_kwh,
        max_charge_acceptance_kw=max_charge_acceptance_kw,
        soc=soc
    )
    geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
    property_link = road_network.property_link_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        powertrain_id=powertrain_id,
        powercurve_id=powercurve_id,
        energy_source=energy_source,
        property_link=property_link
    )


def mock_vehicle_from_geoid(
        vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
        geoid: GeoId = h3.geo_to_h3(0, 0, 15),
        powertrain_id: str = DefaultIds.mock_powertrain_id(),
        powercurve_id: str = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        capacity_kwh: KwH = 100,
        soc: Ratio = 0.25,
        ideal_energy_limit_kwh=50.0,
        max_charge_acceptance_kw: Kw = 50.0,
        road_network: RoadNetwork = mock_network(h3_res=15)
) -> Vehicle:
    energy_source = mock_energy_source(
        powercurve_id=powercurve_id,
        energy_type=energy_type,
        capacity_kwh=capacity_kwh,
        ideal_energy_limit_kwh=ideal_energy_limit_kwh,
        max_charge_acceptance_kw=max_charge_acceptance_kw,
        soc=soc
    )

    property_link = road_network.property_link_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        powertrain_id=powertrain_id,
        powercurve_id=powercurve_id,
        energy_source=energy_source,
        property_link=property_link
    )


def mock_powertrain(
        powertrain_id: PowertrainId = DefaultIds.mock_powertrain_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        energy_cost_kwh: KwH = 0.01
) -> Powertrain:
    class MockPowertrain(Powertrain):
        def get_id(self) -> PowertrainId:
            return powertrain_id

        def get_energy_type(self) -> EnergyType:
            return energy_type

        def energy_cost(self, route: Route) -> KwH:
            return energy_cost_kwh

    return MockPowertrain()


def mock_powercurve(
        powercurve_id: PowercurveId = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC
) -> Powercurve:
    class MockPowercurve(Powercurve):
        def get_id(self) -> PowercurveId:
            return powercurve_id

        def get_energy_type(self) -> EnergyType:
            return energy_type

        def refuel(self, energy_source: EnergySource, charger: Charger,
                   duration_seconds: Seconds = 1) -> EnergySource:
            added_kwh = charger.power_kw * (duration_seconds * SECONDS_TO_HOURS)
            updated_energy_source = energy_source.load_energy(added_kwh)
            return updated_energy_source

    return MockPowercurve()


def mock_sim(
        sim_time: SimTime = 0,
        sim_timestep_duration_seconds: Seconds = 60,
        h3_location_res: int = 15,
        h3_search_res: int = 10,
        vehicles: Tuple[Vehicle, ...] = (),
        stations: Tuple[Station, ...] = (),
        bases: Tuple[Base, ...] = (),
) -> SimulationState:
    sim = SimulationState(
        road_network=mock_network(h3_location_res),
        sim_time=sim_time,
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_location_resolution=h3_location_res,
        sim_h3_search_resolution=h3_search_res,
    )
    if isinstance(sim, Exception):
        raise sim

    sim_v = ft.reduce(lambda s, veh: s.add_vehicle(veh), vehicles, sim) if vehicles else sim
    if isinstance(sim_v, Exception):
        raise sim_v

    sim_s = ft.reduce(lambda s, sta: s.add_station(sta), stations, sim_v) if stations else sim_v
    if isinstance(sim_s, Exception):
        raise sim_s

    sim_b = ft.reduce(lambda s, bas: s.add_base(bas), bases, sim_s) if bases else sim_s
    if isinstance(sim_b, Exception):
        raise sim_b

    return sim_b


def mock_config(
        start_time: Union[str, int] = 0,
        end_time: Union[str, int] = 100,
        timestep_duration_seconds: Seconds = 1,
        sim_h3_location_resolution: int = 15,
        sim_h3_search_resolution: int = 9,
) -> HiveConfig:
    return HiveConfig.build({
        "sim": {
            'start_time': start_time,
            'end_time': end_time,
            'timestep_duration_seconds': timestep_duration_seconds,
            'sim_h3_resolution': sim_h3_location_resolution,
            'sim_h3_search_resolution': sim_h3_search_resolution,
            'sim_name': 'test_sim',
        },
        "io": {
            'vehicles_file': '',
            'requests_file': '',
            'rate_structure_file': '',
            'bases_file': '',
            'stations_file': '',
        }

    })


def mock_env(
        config: HiveConfig = mock_config(),
        powercurves: Optional[Dict[PowercurveId, Powercurve]] = None,
        powertrains: Optional[Dict[PowertrainId, Powertrain]] = None,
) -> Environment:
    if powercurves is None:
        powercurves = {mock_powercurve().get_id(): mock_powercurve()}
    if powertrains is None:
        powertrains = {mock_powertrain().get_id(): mock_powertrain()}

    env = Environment(
        config=config,
        powertrains=powertrains,
        powercurves=powercurves,
    )
    return env


def mock_runner(config: HiveConfig = mock_config()) -> LocalSimulationRunner:
    return LocalSimulationRunner(env=mock_env(config=config))


def mock_reporter() -> Reporter:
    class MockReporter(Reporter):
        def report(self,
                   sim_state: SimulationState,
                   reports: Tuple[str, ...]):
            pass

    return MockReporter()


def mock_haversine_zigzag_route(
        n: int = 3,
        lat_step_size: int = 5,
        lon_step_size: int = 5,
        speed_kmph: Kmph = 40,
        h3_res: int = 15
) -> Route:
    """
    "zigs" lat steps and "zags" lon steps. all your base belong to us.
    :param n: number of steps
    :param lat_step_size: lat-wise step size
    :param lon_step_size: lon-wise step size
    :param speed_kmph: road speed
    :param h3_res: h3 resolution
    :return: a route
    """

    def step(acc: Tuple[PropertyLink, ...], i: int) -> Tuple[PropertyLink, ...]:
        """
        constructs the next PropertyLink
        :param acc: the route so far
        :param i: what link we are making
        :return: the route with another link added
        """
        lat_pos, lon_pos = math.floor(i / 2.0) * lat_step_size, math.floor((i + 1) / 2.0) * lon_step_size
        lat_dest, lon_dest = math.floor((i + 1) / 2.0) * lat_step_size, math.floor((i + 2) / 2.0) * lon_step_size
        link = Link(f"link_{i}", h3.geo_to_h3(lat_pos, lon_pos, h3_res), h3.geo_to_h3(lat_dest, lon_dest, h3_res))
        p = PropertyLink.build(link, speed_kmph)
        return acc + (p,)

    return ft.reduce(step, range(0, n), ())


def mock_graph_links(h3_res: int = 15, speed_kmph: Kmph = 1) -> Dict[str, PropertyLink]:
    """
    test_routetraversal is dependent on this graph topology + its attributes
    """

    links = {
        "1": Link("1",
                  h3.geo_to_h3(37, 122, h3_res),
                  h3.geo_to_h3(37.008994, 122, h3_res)),
        "2": Link("2",
                  h3.geo_to_h3(37.008994, 122, h3_res),
                  h3.geo_to_h3(37.017998, 122, h3_res)),
        "3": Link("3",
                  h3.geo_to_h3(37.017998, 122, h3_res),
                  h3.geo_to_h3(37.026992, 122, h3_res)),
    }

    property_links = {
        # distance of 1.0 KM, speed of 1 KM/time unit
        "1": PropertyLink.build(links["1"], speed_kmph),
        "2": PropertyLink.build(links["2"], speed_kmph),
        "3": PropertyLink.build(links["3"], speed_kmph)
    }
    return property_links


def mock_route(h3_res: int = 15, speed_kmph: Kmph = 1) -> Tuple[PropertyLink, ...]:
    return tuple(mock_graph_links(h3_res=h3_res, speed_kmph=speed_kmph).values())


def mock_graph_network(links: Optional[Dict[str, PropertyLink]] = None, h3_res: int = 15) -> RoadNetwork:
    links = mock_graph_links(h3_res=h3_res) if links is None else links

    class MockGraphNetwork(RoadNetwork):
        """
        a road network that has a fixed set of network links and only implements "get_link"
        """

        def __init__(self, property_links: Dict[str, PropertyLink], h3_res: int):
            self.sim_h3_resolution = h3_res

            self.property_links = property_links

        def route(self, origin: GeoId, destination: GeoId) -> Tuple[Link, ...]:
            pass

        def update(self, sim_time: SimTime) -> RoadNetwork:
            pass

        def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
            if link_id in self.property_links:
                return self.property_links[link_id]
            else:
                return None

        def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
            link_id = property_link.link.link_id
            if link_id in self.property_links:
                current_property_link = self.property_links[link_id]
                updated_property_link = property_link.update_speed(current_property_link.speed_kmph)
                return updated_property_link
            else:
                return None

        def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
            pass

        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            pass

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            pass

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            pass

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            pass

    return MockGraphNetwork(links, h3_res)


def mock_forecaster() -> ForecasterInterface:
    class MockForecaster(NamedTuple, ForecasterInterface):
        def generate_forecast(
                self,
                simulation_state: SimulationState
        ) -> Tuple[ForecasterInterface, Forecast]:
            forecast = Forecast(type=ForecastType.DEMAND, value=1)
            return self, forecast

    return MockForecaster()


def mock_manager(forecaster: ForecasterInterface) -> ManagerInterface:
    class MockManager(NamedTuple, ManagerInterface):
        forecaster: ForecasterInterface

        def generate_fleet_target(
                self,
                simulation_state: SimulationState
        ) -> Tuple[ManagerInterface, FleetStateTarget]:
            active_set = frozenset({
                VehicleState.IDLE,
                VehicleState.SERVICING_TRIP,
                VehicleState.DISPATCH_TRIP,
                VehicleState.DISPATCH_STATION,
                VehicleState.CHARGING_STATION,
                VehicleState.REPOSITIONING,
            })

            _, future_demand = self.forecaster.generate_forecast(simulation_state)

            active_target = StateTarget(id='ACTIVE',
                                        state_set=active_set,
                                        n_vehicles=future_demand.value)

            fleet_state_target = {active_target.id: active_target}

            return self, fleet_state_target

    return MockManager(forecaster=forecaster)
