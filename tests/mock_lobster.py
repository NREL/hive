import functools as ft
import math
from typing import Dict, Union, Callable

import immutables
from h3 import h3
from pkg_resources import resource_filename

from hive.config import HiveConfig
from hive.config.dispatcher_config import DispatcherConfig
from hive.dispatcher.forecaster.forecast import Forecast, ForecastType
from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from hive.dispatcher.instruction_generator.base_fleet_manager import BaseFleetManager
from hive.dispatcher.instruction_generator.position_fleet_manager import PositionFleetManager
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.model.base import Base
from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powercurve import Powercurve
from hive.model.energy.powertrain import Powertrain
from hive.model.request import Request, RequestRateStructure
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.osm_roadnetwork import OSMRoadNetwork
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.vehicle import VehicleType
from hive.reporting.reporter import Reporter
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.step_simulation import StepSimulation
from hive.state.simulation_state.update.update import Update
from hive.state.vehicle_state import VehicleState, Idle
from hive.util.helpers import H3Ops
from hive.util.typealiases import *
from hive.util.units import KwH, Kw, Ratio, Kmph, Seconds, SECONDS_TO_HOURS, Currency, Kilometers


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

    @classmethod
    def mock_vehicle_type_id(cls) -> VehicleTypeId:
        return "vt0"


def mock_geojson() -> Dict:
    return {'type': 'Feature',
            'properties': {'id': None},
            'geometry': {'type': 'Polygon',
                         'coordinates': [[[-105.00029227609865, 39.74962517224048],
                                          [-104.98738065320869, 39.73994639686878],
                                          [-104.97341667234025, 39.74000864414065],
                                          [-104.97337619703339, 39.767951988786585],
                                          [-104.97511663522859, 39.769196417473],
                                          [-105.00029227609865, 39.74962517224048]]]}}


def mock_geofence(geojson: Dict = mock_geojson(), resolution: H3Resolution = 10) -> GeoFence:
    return GeoFence.from_geojson(geojson, resolution)


def mock_network(h3_res: H3Resolution = 15, geofence_res: H3Resolution = 10) -> RoadNetwork:
    return HaversineRoadNetwork(
        geofence=mock_geofence(resolution=geofence_res),
        sim_h3_resolution=h3_res,
    )


def mock_osm_network(h3_res: H3Resolution = 15, geofence_res: H3Resolution = 10) -> OSMRoadNetwork:
    road_network_file = resource_filename('hive.resources.road_network', 'downtown_denver.xml')
    return OSMRoadNetwork(
        road_network_file=road_network_file,
        geofence=mock_geofence(resolution=geofence_res),
        sim_h3_resolution=h3_res,
    )


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
        lat: float = 39.7539,
        lon: float = -104.974,
        h3_res: int = 15,
        station_id: Optional[StationId] = None,
        stall_count: int = 1,
        road_network: RoadNetwork = mock_network(),
) -> Base:
    return Base.build(base_id,
                      h3.geo_to_h3(lat, lon, h3_res),
                      road_network,
                      station_id,
                      stall_count,
                      )


def mock_base_from_geoid(
        base_id: BaseId = DefaultIds.mock_base_id(),
        geoid: GeoId = h3.geo_to_h3(39.7539, -104.9740, 15),
        station_id: Optional[StationId] = None,
        stall_count: int = 1,
        road_network: RoadNetwork = mock_network(),
) -> Base:
    return Base.build(base_id, geoid, road_network, station_id, stall_count)


def mock_station(
        station_id: StationId = DefaultIds.mock_station_id(),
        lat: float = 39.7539,
        lon: float = -104.974,
        h3_res: int = 15,
        chargers=None,
        road_network: RoadNetwork = mock_network(),
) -> Station:
    if chargers is None:
        chargers = immutables.Map({Charger.LEVEL_2: 1, Charger.DCFC: 1})
    return Station.build(station_id, h3.geo_to_h3(lat, lon, h3_res), road_network, chargers)


def mock_station_from_geoid(
        station_id: StationId = DefaultIds.mock_station_id(),
        geoid: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
        chargers=None,
        road_network: RoadNetwork = mock_network()
) -> Station:
    if chargers is None:
        chargers = immutables.Map({Charger.LEVEL_2: 1, Charger.DCFC: 1})
    return Station.build(station_id, geoid, road_network, chargers)


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
        o_lat: float = 39.7539,
        o_lon: float = -104.974,
        d_lat: float = 39.7579,
        d_lon: float = -104.978,
        h3_res: int = 15,
        road_network: RoadNetwork = mock_network(),
        departure_time: SimTime = 0,
        cancel_time: SimTime = 5,
        passengers: int = 1
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=h3.geo_to_h3(o_lat, o_lon, h3_res),
        destination=h3.geo_to_h3(d_lat, d_lon, h3_res),
        road_network=road_network,
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers
    )


def mock_request_from_geoids(
        request_id: RequestId = DefaultIds.mock_request_id(),
        origin: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
        destination: GeoId = h3.geo_to_h3(39.7579, -104.978, 15),
        road_network: RoadNetwork = mock_network(),
        departure_time: SimTime = 0,
        cancel_time: SimTime = 5,
        passengers: int = 1,
        value: Currency = 0
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=origin,
        destination=destination,
        road_network=road_network,
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers,
        value=value,
    )


def mock_vehicle_type(powertrain_id: str = DefaultIds.mock_powertrain_id(),
                      powercurve_id: str = DefaultIds.mock_powercurve_id(),
                      capacity_kwh: KwH = 100,
                      ideal_energy_limit_kwh=50.0,
                      max_charge_acceptance_kw: Kw = 50.0,
                      operating_cost_km: Currency = 0.1, ) -> VehicleType:
    return VehicleType(
        powertrain_id=powertrain_id,
        powercurve_id=powercurve_id,
        capacity_kwh=capacity_kwh,
        ideal_energy_limit_kwh=ideal_energy_limit_kwh,
        max_charge_acceptance=max_charge_acceptance_kw,
        operating_cost_km=operating_cost_km
    )


def mock_vehicle(
        vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
        lat: float = 39.7539,
        lon: float = -104.974,
        h3_res: int = 15,
        powertrain_id: str = DefaultIds.mock_powertrain_id(),
        powercurve_id: str = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        capacity_kwh: KwH = 100,
        soc: Ratio = 0.25,
        ideal_energy_limit_kwh=50.0,
        max_charge_acceptance_kw: Kw = 50.0,
        operating_cost_km: Currency = 0.1,
        vehicle_state: Optional[VehicleState] = None,

) -> Vehicle:
    state = vehicle_state if vehicle_state else Idle(vehicle_id)
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
    link = road_network.link_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        powertrain_id=powertrain_id,
        powercurve_id=powercurve_id,
        energy_source=energy_source,
        link=link,
        operating_cost_km=operating_cost_km,
        vehicle_state=state,
    )


def mock_vehicle_from_geoid(
        vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
        geoid: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
        powertrain_id: str = DefaultIds.mock_powertrain_id(),
        powercurve_id: str = DefaultIds.mock_powercurve_id(),
        energy_type: EnergyType = EnergyType.ELECTRIC,
        capacity_kwh: KwH = 100,
        soc: Ratio = 0.25,
        ideal_energy_limit_kwh=50.0,
        max_charge_acceptance_kw: Kw = 50.0,
        road_network: RoadNetwork = mock_network(h3_res=15),
        operating_cost_km: Currency = 0.1,
        vehicle_state: Optional[VehicleState] = None
) -> Vehicle:
    state = vehicle_state if vehicle_state else Idle(vehicle_id)
    energy_source = mock_energy_source(
        powercurve_id=powercurve_id,
        energy_type=energy_type,
        capacity_kwh=capacity_kwh,
        ideal_energy_limit_kwh=ideal_energy_limit_kwh,
        max_charge_acceptance_kw=max_charge_acceptance_kw,
        soc=soc
    )

    link = road_network.link_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        powertrain_id=powertrain_id,
        powercurve_id=powercurve_id,
        energy_source=energy_source,
        link=link,
        operating_cost_km=operating_cost_km,
        vehicle_state=state
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
        road_network=mock_network(),
        sim_time=sim_time,
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_location_resolution=h3_location_res,
        sim_h3_search_resolution=h3_search_res,
    )

    def add_or_throw(fn: Callable):
        """
        test writers will be told if their added stations, vehicles, or bases are invalid
        :param fn: the sim add function
        :return: the updated sim
        ;raises: Exception when an add fails
        """

        def _inner(s: SimulationState, to_add):
            error, result = fn(s, to_add)
            if error:
                raise error
            else:
                return result

        return _inner

    sim_v = ft.reduce(add_or_throw(simulation_state_ops.add_vehicle), vehicles, sim) if vehicles else sim
    sim_s = ft.reduce(add_or_throw(simulation_state_ops.add_station), stations, sim_v) if stations else sim_v
    sim_b = ft.reduce(add_or_throw(simulation_state_ops.add_base), bases, sim_s) if bases else sim_s

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
            'bases_file': '',
            'stations_file': '',
            'charging_price_file': 'denver_charging_prices_by_geoid.csv',
            'rate_structure_file': 'rate_structure.csv',
            'vehicle_types_file': 'default_vehicle_types.csv',
            'geofence_file': 'downtown_denver.geojson',
            'demand_forecast_file': 'nyc_demand.csv'
        },
        "network": {},
        "dispatcher": {}
    })


def mock_env(
        config: HiveConfig = mock_config(),
        powercurves: Optional[Tuple[Powercurve, ...]] = None,
        powertrains: Optional[Tuple[Powertrain, ...]] = None
) -> Environment:
    if powercurves is None:
        powercurves = (mock_powercurve(),)
    if powertrains is None:
        powertrains = (mock_powertrain(),)
    vehicle_types = immutables.Map({DefaultIds.mock_vehicle_type_id(): mock_vehicle_type()})

    initial_env = Environment(
        config=config,
        reporter=mock_reporter(),
        vehicle_types=vehicle_types
    )

    env_pc = ft.reduce(lambda e, pc: e.add_powercurve(pc), powercurves, initial_env)
    env = ft.reduce(lambda e, pt: e.add_powertrain(pt), powertrains, env_pc)

    return env


def mock_reporter() -> Reporter:
    class MockReporter(Reporter):
        sim_log_file = None

        def log_sim_state(self,
                          sim_state: SimulationState,
                          ):
            pass

        def sim_report(self, report: dict):
            pass

        def single_report(self, report: str):
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

    def step(acc: Tuple[Link, ...], i: int) -> Tuple[Link, ...]:
        """
        constructs the next Link
        :param acc: the route so far
        :param i: what link we are making
        :return: the route with another link added
        """
        lat_pos, lon_pos = math.floor(i / 2.0) * lat_step_size, math.floor((i + 1) / 2.0) * lon_step_size
        lat_dest, lon_dest = math.floor((i + 1) / 2.0) * lat_step_size, math.floor((i + 2) / 2.0) * lon_step_size
        start = h3.geo_to_h3(lat_pos, lon_pos, h3_res)
        end = h3.geo_to_h3(lat_dest, lon_dest, h3_res)
        distance_km = H3Ops.great_circle_distance(start, end)
        link = Link(
            link_id=f"link_{i}",
            start=start,
            end=end,
            distance_km=distance_km,
            speed_kmph=speed_kmph,
        )
        return acc + (link,)

    return ft.reduce(step, range(0, n), ())


def mock_route_from_geoids(
        src: GeoId,
        dst: GeoId,
        speed_kmph: Kmph = 1) -> Tuple[Link, ...]:
    link = Link.build("1", src, dst, speed_kmph=speed_kmph)
    return link,


def mock_graph_links(h3_res: int = 15, speed_kmph: Kmph = 1) -> Dict[str, Link]:
    """
    test_routetraversal is dependent on this graph topology + its attributes
    """

    links = {
        "1": Link.build("1",
                        h3.geo_to_h3(37, 122, h3_res),
                        h3.geo_to_h3(37.008994, 122, h3_res),
                        speed_kmph=speed_kmph,
                        ),
        "2": Link.build("2",
                        h3.geo_to_h3(37.008994, 122, h3_res),
                        h3.geo_to_h3(37.017998, 122, h3_res),
                        speed_kmph=speed_kmph),
        "3": Link.build("3",
                        h3.geo_to_h3(37.017998, 122, h3_res),
                        h3.geo_to_h3(37.026992, 122, h3_res),
                        speed_kmph=speed_kmph),
    }

    return links


def mock_route(h3_res: int = 15, speed_kmph: Kmph = 1) -> Tuple[Link, ...]:
    return tuple(mock_graph_links(h3_res=h3_res, speed_kmph=speed_kmph).values())


def mock_graph_network(links: Optional[Dict[str, Link]] = None, h3_res: int = 15) -> RoadNetwork:
    links = mock_graph_links(h3_res=h3_res) if links is None else links

    class MockGraphNetwork(RoadNetwork):
        """
        a road network that has a fixed set of network links and only implements "get_link"
        """

        def __init__(self, links: Dict[str, Link], h3_res: int):
            self.sim_h3_resolution = h3_res

            self.links = links

        def route(self, origin: GeoId, destination: GeoId) -> Tuple[Link, ...]:
            pass

        def distance_km(self, origin: Link, destination: Link) -> Kilometers:
            pass

        def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
            pass

        def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
            pass

        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            return True

    return MockGraphNetwork(links, h3_res)


def mock_forecaster(forecast: int = 1) -> ForecasterInterface:
    class MockForecaster(NamedTuple, ForecasterInterface):
        def generate_forecast(
                self,
                simulation_state: SimulationState
        ) -> Tuple[ForecasterInterface, Forecast]:
            f = Forecast(type=ForecastType.DEMAND, value=forecast)
            return self, f

    return MockForecaster()


def mock_instruction_generators_with_mock_forecast(
        config: HiveConfig = mock_config(),
        forecast: int = 1) -> Tuple[InstructionGenerator, ...]:
    return (
        BaseFleetManager(config.dispatcher.base_vehicles_charging_limit),
        PositionFleetManager(mock_forecaster(forecast),
                             config.dispatcher.fleet_sizing_update_interval_seconds),
        ChargingFleetManager(config.dispatcher.charging_low_soc_threshold,
                                 config.dispatcher.charging_max_search_radius_km),
        Dispatcher(config.dispatcher.matching_low_soc_threshold),
    )


def mock_update(config: Optional[HiveConfig] = None,
                instruction_generators: Optional[Tuple[InstructionGenerator, ...]] = None) -> Update:
    if config and instruction_generators:
        return Update.build(config.io, instruction_generators)
    elif config:
        instruction_generators = mock_instruction_generators_with_mock_forecast(config)
        return Update.build(config.io, instruction_generators)
    elif instruction_generators:
        config = mock_config()
        return Update.build(config.io, instruction_generators)
    else:
        conf = mock_config()
        instruction_generators = mock_instruction_generators_with_mock_forecast(conf)
        return Update((), StepSimulation(instruction_generators))
