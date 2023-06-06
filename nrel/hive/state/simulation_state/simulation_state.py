from __future__ import annotations

from typing import (
    NamedTuple,
    Optional,
    cast,
    Tuple,
    Callable,
    TYPE_CHECKING,
    FrozenSet,
)

import immutables

from nrel.hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from nrel.hive.model.sim_time import SimTime
from nrel.hive.state.simulation_state.at_location_response import AtLocationResponse
from nrel.hive.util import geo
from nrel.hive.util.dict_ops import DictOps
from nrel.hive.util.typealiases import (
    RequestId,
    VehicleId,
    BaseId,
    StationId,
    GeoId,
)

if TYPE_CHECKING:
    from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
    from nrel.hive.util.units import Seconds
    from nrel.hive.model.base import Base
    from nrel.hive.model.request import Request
    from nrel.hive.model.station.station import Station
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.dispatcher.instruction.instruction import Instruction


class SimulationState(NamedTuple):
    """
    resolution of '11' is within 25 meters/82 feet. this decides how granular
    the simulation will operate for internal operations. the user can still
    specify their own level of granularity for
    https://uber.github.io/h3/#/documentation/core-library/resolution-table
    """

    # road network representation
    road_network: RoadNetwork = HaversineRoadNetwork()

    # simulation parameters
    sim_time: SimTime = SimTime(0)
    sim_timestep_duration_seconds: Seconds = 60
    sim_h3_location_resolution: int = 15
    sim_h3_search_resolution: int = 7

    # objects of the simulation.
    # note: if you need to iterate on these collections, prefer the get methods
    # provided below which ensure entities are properly sorted.
    stations: immutables.Map[StationId, Station] = immutables.Map()
    bases: immutables.Map[BaseId, Base] = immutables.Map()
    vehicles: immutables.Map[VehicleId, Vehicle] = immutables.Map()
    requests: immutables.Map[RequestId, Request] = immutables.Map()

    # the instructions applied in the most recent state transition
    applied_instructions: immutables.Map[VehicleId, Instruction] = immutables.Map()

    # location collections - the lowest-level spatial representation in Hive
    v_locations: immutables.Map[GeoId, FrozenSet[VehicleId]] = immutables.Map()
    r_locations: immutables.Map[GeoId, FrozenSet[RequestId]] = immutables.Map()
    s_locations: immutables.Map[GeoId, FrozenSet[StationId]] = immutables.Map()
    b_locations: immutables.Map[GeoId, FrozenSet[StationId]] = immutables.Map()

    # search collections   - a higher-level spatial representation used for ring search
    v_search: immutables.Map[GeoId, FrozenSet[VehicleId]] = immutables.Map()
    r_search: immutables.Map[GeoId, FrozenSet[RequestId]] = immutables.Map()
    s_search: immutables.Map[GeoId, FrozenSet[StationId]] = immutables.Map()
    b_search: immutables.Map[GeoId, FrozenSet[BaseId]] = immutables.Map()

    def get_station_ids(self) -> Tuple[StationId, ...]:
        return tuple(sorted(self.stations.keys()))

    def get_vehicle_ids(self) -> Tuple[VehicleId, ...]:
        return tuple(sorted(self.vehicles.keys()))

    def get_base_ids(self) -> Tuple[BaseId, ...]:
        return tuple(sorted(self.bases.keys()))

    def get_request_ids(self) -> Tuple[RequestId, ...]:
        return tuple(sorted(self.requests.keys()))

    def get_stations(
        self,
        filter_function: Optional[Callable[[Station], bool]] = None,
        sort_key: Optional[Callable] = None,
    ) -> Tuple[Station, ...]:
        return DictOps.iterate_sim_coll(self.stations, filter_function, sort_key)

    def get_bases(
        self,
        filter_function: Optional[Callable[[Base], bool]] = None,
        sort_key: Optional[Callable] = None,
    ) -> Tuple[Base, ...]:
        return DictOps.iterate_sim_coll(self.bases, filter_function, sort_key)

    def get_vehicles(
        self,
        filter_function: Optional[Callable[[Vehicle], bool]] = None,
        sort_key: Optional[Callable] = None,
    ) -> Tuple[Vehicle, ...]:
        return DictOps.iterate_sim_coll(self.vehicles, filter_function, sort_key)

    def get_requests(
        self,
        filter_function: Optional[Callable[[Request], bool]] = None,
        sort_key: Optional[Callable] = None,
    ) -> Tuple[Request, ...]:
        return DictOps.iterate_sim_coll(self.requests, filter_function, sort_key)

    def at_geoid(self, geoid: GeoId) -> AtLocationResponse:
        """
        returns a dictionary with the list of ids found at this location for all entities

        :deprecated: no longer used
        :param geoid: geoid to look up, should be at the self.sim_h3_location_resolution
        :return: an Optional AtLocationResponse
        """
        vehicles = self.v_locations[geoid] if geoid in self.v_locations else frozenset()
        requests = self.r_locations[geoid] if geoid in self.r_locations else frozenset()
        station = self.s_locations[geoid] if geoid in self.s_locations else frozenset()
        base = self.b_locations[geoid] if geoid in self.b_locations else frozenset()

        result = cast(
            AtLocationResponse,
            {
                "vehicles": vehicles,
                "requests": requests,
                "station": station,
                "base": base,
            },
        )
        return result

    def vehicle_at_request(
        self,
        vehicle_id: VehicleId,
        request_id: RequestId,
        override_resolution: Optional[int] = None,
    ) -> bool:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution


        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param request_id: the request we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        request = self.requests.get(request_id)
        if not vehicle or not request:
            return False
        else:
            return geo.same_simulation_location(
                vehicle.geoid,
                request.origin,
                self.sim_h3_location_resolution,
                override_resolution,
            )

    def vehicle_at_station(
        self,
        vehicle_id: VehicleId,
        station_id: StationId,
        override_resolution: Optional[int] = None,
    ) -> bool:
        """
        tests whether vehicle is at the station within the scope of the given geoid resolution


        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param station_id: the station we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        station = self.stations.get(station_id)
        if not vehicle or not station:
            return False
        else:
            return geo.same_simulation_location(
                vehicle.geoid,
                station.geoid,
                self.sim_h3_location_resolution,
                override_resolution,
            )

    def vehicle_at_base(
        self,
        vehicle_id: VehicleId,
        base_id: BaseId,
        override_resolution: Optional[int] = None,
    ) -> bool:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution


        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param base_id: the base we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        base = self.bases.get(base_id)
        if not vehicle or not base:
            return False
        else:
            return geo.same_simulation_location(
                vehicle.geoid,
                base.geoid,
                self.sim_h3_location_resolution,
                override_resolution,
            )
