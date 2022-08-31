import functools as ft
import math
import tempfile
from pathlib import Path
from typing import Dict

import h3
import immutables
import yaml
from pkg_resources import resource_filename

from returns.result import ResultE, Success, Failure

from hive.config import HiveConfig
from hive.dispatcher.forecaster.forecast import Forecast, ForecastType
from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator.charging_fleet_manager import (
    ChargingFleetManager,
)
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)
from hive.model.base import Base
from hive.model.energy.charger import Charger
from hive.model.energy.energytype import EnergyType
from hive.model.membership import Membership
from hive.model.request import Request, RequestRateStructure
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route
from hive.model.sim_time import SimTime
from hive.model.station.station import Station
from hive.model.vehicle.mechatronics.bev import BEV
from hive.model.vehicle.mechatronics.ice import ICE
from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from hive.model.vehicle.mechatronics.powercurve.tabular_powercurve import (
    TabularPowercurve,
)
from hive.model.vehicle.mechatronics.powertrain.tabular_powertrain import (
    TabularPowertrain,
)
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.reporter import Reporter
from hive.runner.environment import Environment
from hive.runner.runner_payload import RunnerPayload
from hive.state.driver_state.autonomous_driver_state.autonomous_available import (
    AutonomousAvailable,
)
from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import (
    AutonomousDriverAttributes,
)
from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import (
    HumanDriverAttributes,
)
from hive.state.driver_state.human_driver_state.human_driver_state import (
    HumanAvailable,
    HumanUnavailable,
)
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.step_simulation import StepSimulation
from hive.state.simulation_state.update.update import Update
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util.h3_ops import H3Ops
from hive.util.typealiases import *
from hive.util.units import *
from hive.util.fp import throw_or_return


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
    def mock_mechatronics_bev_id(cls) -> MechatronicsId:
        return "bev"

    @classmethod
    def mock_mechatronics_ice_id(cls) -> MechatronicsId:
        return "ice"

    @classmethod
    def mock_schedule_id(cls) -> ScheduleId:
        return "schedule0"

    @classmethod
    def mock_membership_id(cls) -> MembershipId:
        return "membership0"


def somewhere() -> GeoId:
    return h3.geo_to_h3(39.7539, -104.974, 15)


def somewhere_else() -> GeoId:
    return h3.geo_to_h3(39.7579, -104.978, 15)


def mock_geojson() -> Dict:
    return {
        "type": "Feature",
        "properties": {"id": None},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-105.00029227609865, 39.74962517224048],
                    [-104.98738065320869, 39.73994639686878],
                    [-104.97341667234025, 39.74000864414065],
                    [-104.97337619703339, 39.767951988786585],
                    [-104.97511663522859, 39.769196417473],
                    [-105.00029227609865, 39.74962517224048],
                ]
            ],
        },
    }


def mock_membership():
    return Membership().from_tuple((DefaultIds.mock_membership_id(),))


def mock_geofence(
    geojson: Dict = mock_geojson(), resolution: H3Resolution = 10
) -> GeoFence:
    return GeoFence.from_geojson(geojson, resolution)


def mock_network(
    h3_res: H3Resolution = 15, geofence_res: H3Resolution = 10
) -> RoadNetwork:
    return HaversineRoadNetwork(
        geofence=mock_geofence(resolution=geofence_res),
        sim_h3_resolution=h3_res,
    )


def mock_osm_network(
    h3_res: H3Resolution = 15, geofence_res: H3Resolution = 10
) -> OSMRoadNetwork:
    road_network_file = resource_filename(
        "hive.resources.scenarios.denver_downtown.road_network",
        "downtown_denver_network.json",
    )
    return OSMRoadNetwork(
        road_network_file=Path(road_network_file),
        geofence=mock_geofence(resolution=geofence_res),
        sim_h3_resolution=h3_res,
    )


def mock_base(
    base_id: BaseId = DefaultIds.mock_base_id(),
    lat: float = 39.7539,
    lon: float = -104.974,
    h3_res: int = 15,
    station_id: Optional[StationId] = None,
    stall_count: int = 1,
    road_network: RoadNetwork = mock_network(),
    membership: Membership = Membership(),
) -> Base:
    return Base.build(
        base_id,
        h3.geo_to_h3(lat, lon, h3_res),
        road_network,
        station_id,
        stall_count,
        membership,
    )


def mock_base_from_geoid(
    base_id: BaseId = DefaultIds.mock_base_id(),
    geoid: GeoId = h3.geo_to_h3(39.7539, -104.9740, 15),
    station_id: Optional[StationId] = None,
    stall_count: int = 1,
    membership: Membership = Membership(),
    road_network: RoadNetwork = mock_network(),
) -> Base:
    return Base.build(base_id, geoid, road_network, station_id, stall_count, membership)


def mock_station(
    station_id: StationId = DefaultIds.mock_station_id(),
    lat: float = 39.7539,
    lon: float = -104.974,
    h3_res: int = 15,
    chargers=None,
    on_shift_access_chargers=None,
    road_network: RoadNetwork = mock_network(),
    membership: Membership = Membership(),
) -> Station:
    hex = h3.geo_to_h3(lat, lon, h3_res)
    return mock_station_from_geoid(
        station_id,
        geoid=hex,
        chargers=chargers,
        on_shift_access_chargers=on_shift_access_chargers,
        road_network=road_network,
        membership=membership,
    )
    # return Station.build(
    #     id=station_id,
    #     geoid=h3.geo_to_h3(lat, lon, h3_res),
    #     road_network=road_network,
    #     charger=mock_l2_charger(),
    #     charger_count=1,
    #     on_shift_access=on_shift_access_chargers,
    #     membership=membership
    # ).add_charger(mock_dcfc_charger())


def mock_station_from_geoid(
    station_id: StationId = DefaultIds.mock_station_id(),
    geoid: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
    chargers=None,
    on_shift_access_chargers=None,
    road_network: RoadNetwork = mock_network(),
    membership: Membership = Membership(),
    env: Optional[Environment] = None,
) -> Station:
    if chargers is None:
        chargers = immutables.Map({mock_l2_charger_id(): 1, mock_dcfc_charger_id(): 1})
    elif isinstance(chargers, dict):
        chargers = immutables.Map(chargers)
    if on_shift_access_chargers is None:
        on_shift_access_chargers = frozenset(chargers.keys())
    if env is None:
        env = mock_env()

    return Station.build(
        id=station_id,
        geoid=geoid,
        road_network=road_network,
        chargers=chargers,
        on_shift_access=on_shift_access_chargers,
        membership=membership,
        env=env,
    )


def mock_rate_structure(
    base_price: Currency = 2.2,
    price_per_mile: Currency = 1.6,
    minimum_price: Currency = 5,
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
    passengers: int = 1,
    fleet_id: Optional[MembershipId] = None,
    allows_pooling: bool = False,
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=h3.geo_to_h3(o_lat, o_lon, h3_res),
        destination=h3.geo_to_h3(d_lat, d_lon, h3_res),
        road_network=road_network,
        departure_time=departure_time,
        passengers=passengers,
        fleet_id=fleet_id,
        allows_pooling=allows_pooling,
    )


def mock_request_from_geoids(
    request_id: RequestId = DefaultIds.mock_request_id(),
    origin: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
    destination: GeoId = h3.geo_to_h3(39.7579, -104.978, 15),
    road_network: RoadNetwork = mock_network(),
    departure_time: SimTime = SimTime(0),
    passengers: int = 1,
    value: Currency = 0,
    fleet_id: Optional[MembershipId] = None,
    allows_pooling: bool = False,
) -> Request:
    return Request.build(
        request_id=request_id,
        origin=origin,
        destination=destination,
        road_network=road_network,
        departure_time=departure_time,
        passengers=passengers,
        value=value,
        fleet_id=fleet_id,
        allows_pooling=allows_pooling,
    )


def mock_ev_powertrain(nominal_watt_hour_per_mile) -> TabularPowertrain:
    powertrain_file = resource_filename(
        "hive.resources.powertrain", "normalized-electric.yaml"
    )
    with Path(powertrain_file).open() as f:
        data = yaml.safe_load(f)
        data["scale_factor"] = nominal_watt_hour_per_mile
        return TabularPowertrain(data=data)


def mock_powercurve(
    nominal_max_charge_kw=50,
    battery_capacity_kwh=50,
) -> TabularPowercurve:
    powercurve_file = resource_filename("hive.resources.powercurve", "normalized.yaml")
    with Path(powercurve_file).open() as f:
        data = yaml.safe_load(f)
        return TabularPowercurve(
            data=data,
            nominal_max_charge_kw=nominal_max_charge_kw,
            battery_capacity_kwh=battery_capacity_kwh,
        )


def mock_bev(
    battery_capacity_kwh=50,
    idle_kwh_per_hour=0.8,
    nominal_watt_hour_per_mile=225,
    nominal_max_charge_kw=50,
    charge_taper_cutoff_kw=10,
) -> BEV:
    return BEV(
        mechatronics_id="bev",
        battery_capacity_kwh=battery_capacity_kwh,
        idle_kwh_per_hour=idle_kwh_per_hour,
        powertrain=mock_ev_powertrain(nominal_watt_hour_per_mile),
        powercurve=mock_powercurve(nominal_max_charge_kw, battery_capacity_kwh),
        nominal_watt_hour_per_mile=nominal_watt_hour_per_mile,
        charge_taper_cutoff_kw=charge_taper_cutoff_kw,
    )


def mock_ice_powertrain(nominal_miles_per_gallon) -> TabularPowertrain:
    powertrain_file = resource_filename(
        "hive.resources.powertrain", "normalized-gasoline.yaml"
    )
    with Path(powertrain_file).open() as f:
        data = yaml.safe_load(f)
        data["scale_factor"] = 1 / nominal_miles_per_gallon
        return TabularPowertrain(data=data)


def mock_ice(
    tank_capacity_gallons=15,
    idle_gallons_per_hour=0.2,
    nominal_miles_per_gallon=30,
) -> ICE:
    # source: https://www.energy.gov/eere/vehicles/
    #   fact-861-february-23-2015-idle-fuel-consumption-selected-gasoline-and-diesel-vehicles
    return ICE(
        mechatronics_id="ice",
        tank_capacity_gallons=tank_capacity_gallons,
        idle_gallons_per_hour=idle_gallons_per_hour,
        nominal_miles_per_gallon=nominal_miles_per_gallon,
        powertrain=mock_ice_powertrain(nominal_miles_per_gallon),
    )


def mock_vehicle(
    vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
    lat: float = 39.7539,
    lon: float = -104.974,
    h3_res: int = 15,
    mechatronics: MechatronicsInterface = mock_bev(),
    vehicle_state: Optional[VehicleState] = None,
    soc: Ratio = 1,
    driver_state: Optional[DriverState] = None,
    membership: Membership = Membership(),
    total_seats: int = 999,
) -> Vehicle:
    v_state = vehicle_state if vehicle_state else Idle.build(vehicle_id)
    road_network = mock_network(h3_res)
    initial_energy = mechatronics.initial_energy(soc)
    geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
    d_state = (
        driver_state
        if driver_state
        else AutonomousAvailable(AutonomousDriverAttributes(vehicle_id))
    )
    position = road_network.position_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        mechatronics_id=mechatronics.mechatronics_id,
        energy=initial_energy,
        position=position,
        vehicle_state=v_state,
        driver_state=d_state,
        membership=membership,
        total_seats=total_seats,
    )


def mock_vehicle_from_geoid(
    vehicle_id: VehicleId = DefaultIds.mock_vehicle_id(),
    geoid: GeoId = h3.geo_to_h3(39.7539, -104.974, 15),
    mechatronics: MechatronicsInterface = mock_bev(),
    vehicle_state: Optional[VehicleState] = None,
    soc: Ratio = 1,
    driver_state: Optional[DriverState] = None,
    membership: Membership = Membership(),
    total_seats: int = 999,
) -> Vehicle:
    state = vehicle_state if vehicle_state else Idle.build(vehicle_id)
    initial_energy = mechatronics.initial_energy(soc)
    d_state = (
        driver_state
        if driver_state
        else AutonomousAvailable(AutonomousDriverAttributes(vehicle_id))
    )
    position = mock_network().position_from_geoid(geoid)
    return Vehicle(
        id=vehicle_id,
        mechatronics_id=mechatronics.mechatronics_id,
        energy=initial_energy,
        position=position,
        vehicle_state=state,
        driver_state=d_state,
        membership=membership,
        total_seats=total_seats,
    )


def mock_human_driver(
    available: bool = True,
    schedule_id: ScheduleId = DefaultIds.mock_schedule_id(),
    home_base_id: BaseId = DefaultIds.mock_base_id(),
    allows_pooling: bool = True,
):
    attr = HumanDriverAttributes(
        DefaultIds.mock_vehicle_id(), schedule_id, home_base_id, allows_pooling
    )
    state = HumanAvailable(attr) if available else HumanUnavailable(attr)
    return state


def mock_runner_payload() -> RunnerPayload:
    return RunnerPayload(mock_sim(), mock_env(), mock_update())


def mock_sim(
    sim_time: int = 0,
    sim_timestep_duration_seconds: Seconds = 60,
    h3_location_res: int = 15,
    h3_search_res: int = 10,
    vehicles: Tuple[Vehicle, ...] = (),
    stations: Tuple[Station, ...] = (),
    bases: Tuple[Base, ...] = (),
    road_network: RoadNetwork = mock_network(),
) -> SimulationState:
    sim = SimulationState(
        road_network=road_network,
        sim_time=SimTime.build(sim_time),
        sim_timestep_duration_seconds=sim_timestep_duration_seconds,
        sim_h3_location_resolution=h3_location_res,
        sim_h3_search_resolution=h3_search_res,
    )

    sim_v = simulation_state_ops.add_entities(sim, vehicles)
    sim_s = simulation_state_ops.add_entities(sim_v, stations)
    sim_b = simulation_state_ops.add_entities(sim_s, bases)

    return sim_b


def mock_config(
    start_time: Union[str, int] = 0,
    end_time: Union[str, int] = 100,
    timestep_duration_seconds: Seconds = 1,
    sim_h3_location_resolution: int = 15,
    sim_h3_search_resolution: int = 9,
    input: Dict = None,
) -> HiveConfig:
    if not input:
        input = {
            "vehicles_file": "denver_demo_vehicles.csv",
            "requests_file": "denver_demo_requests.csv",
            "bases_file": "denver_demo_bases.csv",
            "stations_file": "denver_demo_stations.csv",
            "chargers_file": "default_chargers.csv",
            "charging_price_file": "denver_charging_prices_by_geoid.csv",
            "rate_structure_file": "rate_structure.csv",
            "mechatronics_file": "mechatronics.yaml",
            "geofence_file": "downtown_denver.geojson",
            "demand_forecast_file": "denver_demand.csv",
        }
    test_output_directory = tempfile.TemporaryDirectory()
    conf_without_temp_dir = HiveConfig.build(
        Path(
            resource_filename(
                "hive.resources.scenarios.denver_downtown", "denver_demo.yaml"
            )
        ),
        {
            "sim": {
                "start_time": start_time,
                "end_time": end_time,
                "timestep_duration_seconds": timestep_duration_seconds,
                "sim_h3_resolution": sim_h3_location_resolution,
                "sim_h3_search_resolution": sim_h3_search_resolution,
                "sim_name": "test_sim",
            },
            "input": input,
            "network": {},
            "dispatcher": {},
        },
    )
    updated_global = conf_without_temp_dir.global_config._replace(
        output_base_directory=test_output_directory.name
    )

    return conf_without_temp_dir._replace(global_config=updated_global)


def mock_env(
    config: HiveConfig = mock_config(),
    mechatronics: Optional[Dict[MechatronicsId, MechatronicsInterface]] = None,
    chargers: Optional[Dict[Charger, Charger]] = None,
    schedules: Optional[
        Dict[ScheduleId, Callable[["SimulationState", VehicleId], bool]]
    ] = None,
    fleet_ids: FrozenSet[MembershipId] = frozenset([DefaultIds.mock_membership_id()]),
) -> Environment:
    if mechatronics is None:
        mechatronics = {
            DefaultIds.mock_mechatronics_bev_id(): mock_bev(),
        }

    if chargers is None:
        chargers = {
            mock_l1_charger_id(): mock_l1_charger(),
            mock_l2_charger_id(): mock_l2_charger(),
            mock_dcfc_charger_id(): mock_dcfc_charger(),
        }

    if schedules is None:

        def always_on_schedule(a, b):
            return True

        schedules = {DefaultIds.mock_schedule_id(): always_on_schedule}

    initial_env = Environment(
        config=config,
        reporter=mock_reporter(),
        mechatronics=immutables.Map(mechatronics),
        chargers=immutables.Map(chargers),
        schedules=immutables.Map(schedules),
        fleet_ids=fleet_ids,
    )

    return initial_env


def mock_reporter() -> Reporter:
    class MockReporter(Reporter):
        def __init__(self):
            super().__init__()

        def flush(self, sim_state: SimulationState):
            pass

        def file_report(self, report: dict):
            pass

        def close(self, runner_payload: RunnerPayload):
            pass

    return MockReporter()


def mock_haversine_zigzag_route(
    n: int = 3,
    lat_step_size: int = 5,
    lon_step_size: int = 5,
    speed_kmph: Kmph = 40,
    h3_res: int = 15,
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
        lat_pos, lon_pos = (
            math.floor(i / 2.0) * lat_step_size,
            math.floor((i + 1) / 2.0) * lon_step_size,
        )
        lat_dest, lon_dest = (
            math.floor((i + 1) / 2.0) * lat_step_size,
            math.floor((i + 2) / 2.0) * lon_step_size,
        )
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
    src: GeoId, dst: GeoId, speed_kmph: Kmph = 1
) -> Tuple[Link, ...]:
    link = Link.build("1", src, dst, speed_kmph=speed_kmph)
    return (link,)


def mock_graph_links(h3_res: int = 15, speed_kmph: Kmph = 1) -> Dict[str, Link]:
    """
    test_routetraversal is dependent on this graph topology + its attributes
    each link is approximately 1 kilometer
    """

    links = {
        "1": Link.build(
            "1",
            h3.geo_to_h3(37, 122, h3_res),
            h3.geo_to_h3(37.008994, 122, h3_res),
            speed_kmph=speed_kmph,
        ),
        "2": Link.build(
            "2",
            h3.geo_to_h3(37.008994, 122, h3_res),
            h3.geo_to_h3(37.017998, 122, h3_res),
            speed_kmph=speed_kmph,
        ),
        "3": Link.build(
            "3",
            h3.geo_to_h3(37.017998, 122, h3_res),
            h3.geo_to_h3(37.026992, 122, h3_res),
            speed_kmph=speed_kmph,
        ),
    }

    return links


def mock_route(h3_res: int = 15, speed_kmph: Kmph = 1) -> Tuple[Link, ...]:
    return tuple(mock_graph_links(h3_res=h3_res, speed_kmph=speed_kmph).values())


def mock_forecaster(forecast: int = 1) -> ForecasterInterface:
    class MockForecaster(NamedTuple, ForecasterInterface):
        def generate_forecast(
            self, simulation_state: SimulationState
        ) -> Tuple[ForecasterInterface, Forecast]:
            f = Forecast(type=ForecastType.DEMAND, value=forecast)
            return self, f

    return MockForecaster()


def mock_instruction_generators(
    config: HiveConfig = mock_config(),
) -> Tuple[InstructionGenerator, ...]:
    return (
        ChargingFleetManager(config.dispatcher),
        Dispatcher(config.dispatcher),
    )


def mock_update(
    config: Optional[HiveConfig] = None,
    instruction_generators: Optional[Tuple[InstructionGenerator, ...]] = None,
) -> Update:
    if config and instruction_generators:
        return Update.build(config, instruction_generators)
    elif config:
        instruction_generators = mock_instruction_generators(config)
        return Update.build(config, instruction_generators)
    elif instruction_generators:
        config = mock_config()
        return Update.build(config, instruction_generators)
    else:
        conf = mock_config()
        instruction_generators = mock_instruction_generators(conf)
        return Update((), StepSimulation.from_tuple(instruction_generators))


def mock_l1_charger_id():
    return "LEVEL_1"


def mock_l2_charger_id():
    return "LEVEL_2"


def mock_dcfc_charger_id():
    return "DCFC"


def mock_l1_charger():
    return Charger(
        mock_l1_charger_id(),
        energy_type=EnergyType.ELECTRIC,
        rate=3.3,
        units="kilowatts",
    )


def mock_l2_charger():
    return Charger(
        mock_l2_charger_id(),
        energy_type=EnergyType.ELECTRIC,
        rate=7.2,
        units="kilowatts",
    )


def mock_dcfc_charger():
    return Charger(
        mock_dcfc_charger_id(),
        energy_type=EnergyType.ELECTRIC,
        rate=50.0,
        units="kilowatts",
    )


def mock_gasoline_pump():
    gal_per_minute = 10  # source: https://en.wikipedia.org/wiki/Gasoline_pump
    gal_per_second = gal_per_minute / 60

    return Charger(
        "gas_pump",
        energy_type=EnergyType.GASOLINE,
        rate=gal_per_second,
        units="gal_gasoline",
    )
