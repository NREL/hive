from __future__ import annotations
from copy import copy
from typing import NamedTuple, Dict, Optional

from hive.model.base import Base
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.util.typealiases import *
from h3 import h3


class SimulationState(NamedTuple):
    # model data required in constructor
    road_network: RoadNetwork
    stations: Dict[StationId, Station]
    bases: Dict[BaseId, Base]
    s_locations: Dict[GeoId, StationId] = {}
    b_locations: Dict[GeoId, Base] = {}

    # model data with default as empty
    vehicles: Dict[VehicleId, Vehicle] = {}
    requests: Dict[RequestId, Request] = {}

    # location lookup collections
    v_locations: Dict[GeoId, VehicleId] = {}
    r_locations: Dict[GeoId, RequestId] = {}

    # todo: a constructor which doesn't expect s + b locations

    # resolution of 11 is within 25 meters/82 feet. this decides how granular
    # the simulation will operate for internal operations. the user can still
    # specify their own level of granularity for
    # https://uber.github.io/h3/#/documentation/core-library/resolution-table
    sim_h3_resolution: int = 11

    def add_request(self, request: Request) -> SimulationState:
        """
        adds a request to the SimulationState
        :param request: the request to add
        :return: the updated simulation state
        """

        request_geoid = h3.geo_to_h3(request.origin.lat, request.origin.lon, self.sim_h3_resolution)
        # TODO: should we do this? push the request to the center of the h3 hex?
        #  that way, given the correct spatial resolution, we should always have
        #  a buffer to overlap vehicles to requests which is equal to the radius
        #  of the spatial resolution?
        geoid_centroid = h3.h3_to_geo(request_geoid)
        new_lat, new_lon = (geoid_centroid[0], geoid_centroid[1])
        updated_request = request.update_origin(new_lat, new_lon)

        updated_requests = copy(self.requests)
        updated_requests.update((updated_request.id, updated_request))

        updated_r_locations = copy(self.r_locations)
        updated_r_locations.update((request_geoid, updated_request.id))

        return self._replace(
            requests=updated_requests,
            r_locations=updated_r_locations
        )

    def remove_request(self, request_id: RequestId) -> SimulationState:
        """
        removes a request from this simulation.
        called once a Request has been fully serviced and is no longer
        alive in the simulation.
        :param request_id: id of the request to delete
        :return: the updated simulation state
        """
        if request_id not in self.requests:
            return self
        else:
            request = self.requests[request_id]
            request_geoid = h3.geo_to_h3(request.origin.lat, request.origin.lon, self.sim_h3_resolution)

            updated_requests = copy(self.requests)
            del updated_requests[request_id]

            updated_r_locations = copy(self.r_locations)
            del updated_r_locations[request_geoid]

            return self._replace(
                requests=updated_requests,
                r_locations=updated_r_locations
            )

    def board_vehicle(self, request_id: RequestId, vehicle_id: VehicleId) -> SimulationState:
        """
        places passengers from a request into a Vehicle
        :param request_id:
        :param vehicle_id:
        :return: updated simulation state
        """
        pass

    def vehicle_at_request(self,
                           vehicle_id: VehicleId,
                           request_id: RequestId,
                           override_resolution: Optional[int]) -> bool:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution
        :param vehicle_id:
        :param request_id:
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_resolution
        :return: bool
        """
        pass

    def get_vehicle_geoid(self, vehicle_id) -> Optional[GeoId]:
        """
        updates the geoid of a vehicle based on the vehicle's coordinate
        :param vehicle_id:
        :return:
        """
        if vehicle_id not in self.vehicles:
            return None
        else:
            vehicle_position = self.vehicles[vehicle_id].position
            vehicle_coordinate = self.road_network.position_to_coordinate(vehicle_position)
            new_geoid = h3.geo_to_h3(vehicle_coordinate.lat, vehicle_coordinate.lon, self.sim_h3_resolution)
            return new_geoid
