from __future__ import annotations

from copy import copy
from typing import NamedTuple, Dict, Optional, Union, Tuple

from h3 import h3

from hive.model.base import Base
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.util.exception import *
from hive.util.helpers import TupleOps
from hive.util.typealiases import *


class SimulationState(NamedTuple):
    # road network representation
    road_network: RoadNetwork

    # simulation parameters
    sim_time: int
    sim_h3_resolution: int

    # objects of the simulation
    stations: Dict[StationId, Station] = {}
    bases: Dict[BaseId, Base] = {}
    vehicles: Dict[VehicleId, Vehicle] = {}
    requests: Dict[RequestId, Request] = {}

    # location lookup collections
    v_locations: Dict[GeoId, Tuple[VehicleId, ...]] = {}
    r_locations: Dict[GeoId, Tuple[RequestId, ...]] = {}
    s_locations: Dict[GeoId, Tuple[StationId, ...]] = {}
    b_locations: Dict[GeoId, Tuple[BaseId, ...]] = {}

    """
    resolution of '11' is within 25 meters/82 feet. this decides how granular
    the simulation will operate for internal operations. the user can still
    specify their own level of granularity for
    https://uber.github.io/h3/#/documentation/core-library/resolution-table
    """

    def add_request(self, request: Request) -> Union[Exception, SimulationState]:
        """
        adds a request to the SimulationState
        :param request: the request to add
        :return: the updated simulation state, or an error
        """
        if not isinstance(request, Request):
            return TypeError(f"sim.add_request requires a request but received a {type(request)}")
        elif not self.road_network.geoid_within_geofence(request.o_geoid):
            return SimulationStateError(f"origin {request.origin} not within road network geofence")
        elif not self.road_network.geoid_within_simulation(request.d_geoid):
            return SimulationStateError(f"destination {request.destination} not within entire road network")
        else:

            updated_requests = copy(self.requests)
            updated_requests.update([(request.id, request)])

            updated_r_locations = copy(self.r_locations)
            ids_at_location = updated_r_locations.get(request.o_geoid, ())
            updated_r_locations.update([(request.o_geoid, (request.id,) + ids_at_location)])

            return self._replace(
                requests=updated_requests,
                r_locations=updated_r_locations
            )

    def remove_request(self, request_id: RequestId) -> Union[Exception, SimulationState]:
        """
        removes a request from this simulation.
        called once a Request has been fully serviced and is no longer
        alive in the simulation.
        :param request_id: id of the request to delete
        :return: the updated simulation state (does not report failure)
        """
        if not isinstance(request_id, RequestId):
            return TypeError(f"remove_request() takes a RequestId (str), not a {type(request_id)}")
        if request_id not in self.requests:
            return SimulationStateError(f"attempting to remove request {request_id} which is not in simulation")
        else:
            request = self.requests[request_id]
            request_geoid = h3.geo_to_h3(request.origin.lat, request.origin.lon, self.sim_h3_resolution)

            updated_requests = copy(self.requests)
            del updated_requests[request_id]

            updated_r_locations = copy(self.r_locations)
            ids_at_location = updated_r_locations[request_geoid]
            updated_ids_at_location = TupleOps.remove(ids_at_location, request_id)
            if updated_ids_at_location is None:
                return SimulationStateError(f"cannot remove request {request_id} at hex {request_geoid}")
            else:

                updated_r_locations[request_geoid] = updated_ids_at_location

                return self._replace(
                    requests=updated_requests,
                    r_locations=updated_r_locations
                )

    def add_vehicle(self, vehicle: Vehicle) -> Union[Exception, SimulationState]:
        """
        adds a vehicle into the region supported by the RoadNetwork in this SimulationState
        :param vehicle: a vehicle
        :return: updated SimulationState, or SimulationStateError
        """
        if not isinstance(vehicle, Vehicle):
            return TypeError(f"sim.add_vehicle requires a vehicle but received {type(vehicle)}")
        elif not self.road_network.geoid_within_geofence(vehicle.geoid):
            return SimulationStateError(f"cannot add vehicle {vehicle.id} to sim: not within road network geofence")
        else:
            updated_vehicles = copy(self.vehicles)
            updated_vehicles.update([(vehicle.id, vehicle)])

            updated_v_locations = copy(self.v_locations)
            ids_at_location = updated_v_locations.get(vehicle.geoid, ())
            updated_v_locations.update([(vehicle.geoid, (vehicle.id,) + ids_at_location)])

            return self._replace(
                vehicles=updated_vehicles,
                v_locations=updated_v_locations
            )

    def update_vehicle(self, updated_vehicle: Vehicle) -> Union[Exception, SimulationState]:
        """
        given an updated vehicle state, update the SimulationState with that vehicle
        :param updated_vehicle: the vehicle after calling a transition function and .step()
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_vehicle, Vehicle):
            return TypeError(f"sim.update_vehicle requires a vehicle but received {type(updated_vehicle)}")
        elif not self.road_network.geoid_within_geofence(updated_vehicle.geoid):
            return SimulationStateError(f"cannot add vehicle {updated_vehicle.id} to sim: not within road network")
        else:
            old_vehicle = self.vehicles[updated_vehicle.id]

            updated_vehicles = copy(self.vehicles)
            updated_vehicles.update([(updated_vehicle.id, updated_vehicle)])

            updated_v_locations = copy(self.v_locations)
            if not old_vehicle.geoid == updated_vehicle.geoid:
                # unset from old geoid add add to new one

                ids_at_old_location: Tuple[VehicleId, ...] = updated_v_locations.get(old_vehicle.geoid, ())
                updated_old_location: Tuple[VehicleId, ...] = TupleOps.remove(ids_at_old_location, updated_vehicle.id)
                ids_at_new_location: Tuple[VehicleId, ...] = updated_v_locations.get(updated_vehicle.geoid, ())
                updated_new_location: Tuple[VehicleId, ...] = (updated_vehicle.id,) + ids_at_new_location
                updated_v_locations.update([
                    (updated_vehicle.geoid, updated_new_location),
                    (old_vehicle.geoid, updated_old_location)
                ])

            return self._replace(
                vehicles=updated_vehicles,
                v_locations=updated_v_locations
            )

    def remove_vehicle(self, vehicle_id: VehicleId) -> Union[Exception, SimulationState]:
        """
        removes the vehicle from play (perhaps to simulate a broken vehicle or end of a shift)
        :param vehicle_id: the id of the vehicle
        :return: the updated simulation state
        """
        if not isinstance(vehicle_id, VehicleId):
            return TypeError(f"remove_request() takes a VehicleId (str), not a {type(vehicle_id)}")
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"attempting to remove vehicle {vehicle_id} which is not in simulation")
        else:
            vehicle = self.vehicles[vehicle_id]

            updated_vehicles = copy(self.vehicles)
            del updated_vehicles[vehicle_id]

            updated_v_locations = copy(self.v_locations)
            ids_at_location = updated_v_locations[vehicle.geoid]
            updated_ids_at_location = TupleOps.remove(ids_at_location, vehicle_id)

            if updated_ids_at_location is None:
                return SimulationStateError(f"cannot remove vehicle {vehicle_id} at hex {vehicle.geoid}")
            else:

                updated_v_locations[vehicle.geoid] = updated_ids_at_location

                return self._replace(
                    vehicles=updated_vehicles,
                    v_locations=updated_v_locations
                )

    def pop_vehicle(self, vehicle_id: VehicleId) -> Union[Exception, Tuple[SimulationState, Vehicle]]:
        """
        removes a vehicle from this SimulationState, which updates the state and also returns the vehicle.
        supports shipping this vehicle to another cluster node.
        :param vehicle_id: the id of the vehicle to pop
        :return: either a Tuple containing the updated state and the vehicle, or, an error
        """
        if not isinstance(vehicle_id, VehicleId):
            return TypeError(f"sim.pop_vehicle requires a vehicle_id (str) but received {type(vehicle_id)}")
        elif vehicle_id not in self.vehicles:
            return SimulationStateError(f"attempting to pop vehicle {vehicle_id} which is not in simulation")
        else:
            remove_result = self.remove_vehicle(vehicle_id)
            if isinstance(remove_result, SimulationStateError):
                return remove_result
            else:
                vehicle = self.vehicles[vehicle_id]
                return remove_result, vehicle

    def add_station(self, station: Station) -> Union[Exception, SimulationState]:
        """
        adds a station to the simulation
        :param station: the station to add
        :return: the updated SimulationState, or a SimulationStateError
        """
        if not isinstance(station, Station):
            return TypeError(f"sim.add_station requires a station but received {type(station)}")
        elif not self.road_network.geoid_within_geofence(station.geoid):
            return SimulationStateError(f"cannot add station {station.id} to sim: not within road network geofence")
        else:
            station_geoid = h3.geo_to_h3(station.coordinate.lat, station.coordinate.lon, self.sim_h3_resolution)

            updated_vehicles = copy(self.stations)
            updated_vehicles.update([(station.id, station)])

            updated_s_locations = copy(self.s_locations)
            ids_at_location = updated_s_locations.get(station_geoid, ())
            updated_s_locations.update([(station_geoid, (station.id,) + ids_at_location)])

            return self._replace(
                stations=updated_vehicles,
                s_locations=updated_s_locations
            )

    def remove_station(self, station_id: StationId) -> Union[Exception, SimulationState]:
        """
        remove a station from the simulation. maybe they closed due to inclement weather.
        :param station_id: the id of the station to remove
        :return: the updated simulation state, or an exception
        """
        if not isinstance(station_id, StationId):
            return TypeError(f"sim.remove_station requires a StationId (str) but received {type(station_id)}")
        elif station_id not in self.stations:
            return SimulationStateError(f"cannot remove station {station_id}, it does not exist")
        else:
            station = self.stations[station_id]
            updated_stations = copy(self.stations)
            del updated_stations[station_id]

            updated_s_locations = copy(self.s_locations)
            del updated_s_locations[station.geoid]

            return self._replace(
                stations=updated_stations,
                s_locations=updated_s_locations
            )

    def add_base(self, base: Base) -> Union[Exception, SimulationState]:
        """
        adds a base to the simulation
        :param base: the base to add
        :return: the updated SimulationState, or a SimulationStateError
        """
        if not isinstance(base, Base):
            return TypeError(f"sim.add_base requires a base but received {type(base)}")
        if not self.road_network.geoid_within_geofence(base.geoid):
            return SimulationStateError(f"cannot add base {base.id} to sim: not within road network geofence")
        else:
            updated_bases = copy(self.bases)
            updated_bases.update([(base.id, base)])

            updated_s_locations = copy(self.b_locations)
            ids_at_location = updated_s_locations.get(base.geoid, ())
            updated_s_locations.update([(base.geoid, (base.id,) + ids_at_location)])

            return self._replace(
                bases=updated_bases,
                b_locations=updated_s_locations
            )

    def remove_base(self, base_id: BaseId) -> Union[Exception, SimulationState]:
        """
        remove a base from the simulation. all your base belong to us.
        :param base_id: the id of the base to remove
        :return: the updated simulation state, or an exception
        """
        if not isinstance(base_id, BaseId):
            return TypeError(f"sim.remove_base requires a BaseId (str) but received {type(base_id)}")
        elif base_id not in self.bases:
            return SimulationStateError(f"cannot remove base {base_id}, it does not exist")
        else:
            base = self.bases[base_id]
            updated_bases = copy(self.bases)
            del updated_bases[base_id]

            updated_s_locations = copy(self.b_locations)
            del updated_s_locations[base.geoid]
            
            return self._replace(
                bases=updated_bases,
                b_locations=updated_s_locations
            )

    def update_road_network(self, sim_time: int) -> SimulationState:
        """
        trigger the update of the road network model based on the current sim time
        :param sim_time: the current sim time
        :return: updated simulation state (and road network)
        """
        return self._replace(
            road_network=self.road_network.update(sim_time)
        )

    @classmethod
    def _same_geoid(cls,
                    a: GeoId,
                    b: GeoId,
                    sim_h3_resolution: int,
                    override_resolution: Optional[int]) -> Union[SimulationStateError, bool]:
        """
        tests if two geoids are the same. allows for overriding test resolution to a parent level
        todo: maybe move this to a geoutility collection somewhere like hive.util._
        :param a: first geoid
        :param b: second geoid
        :param override_resolution: an overriding h3 spatial resolution, or, none to use this sim's default res
        :return: True/False, or, a SimulationStateError
        """
        if override_resolution is None:
            return a == b
        elif override_resolution > sim_h3_resolution:
            return SimulationStateError(
                f"cannot override geoid resolution {sim_h3_resolution} to smaller hex {override_resolution}")
        elif override_resolution == sim_h3_resolution:
            return a == b
        else:
            a_parent = h3.h3_to_parent(a, override_resolution)
            b_parent = h3.h3_to_parent(b, override_resolution)
            return a_parent == b_parent

    def vehicle_at_request(self,
                           vehicle_id: VehicleId,
                           request_id: RequestId,
                           override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution
        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param request_id: the request we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif request_id not in self.requests:
            return SimulationStateError(f"request {request_id} not in this simulation")
        else:
            vehicle = self.vehicles[vehicle_id].geoid
            request = self.requests[request_id].o_geoid

            return SimulationState._same_geoid(vehicle, request, self.sim_h3_resolution, override_resolution)

    def vehicle_at_station(self,
                           vehicle_id: VehicleId,
                           station_id: StationId,
                           override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the station within the scope of the given geoid resolution
        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param station_id: the station we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif station_id not in self.stations:
            return SimulationStateError(f"station {station_id} not in this simulation")
        else:
            vehicle = self.vehicles[vehicle_id].geoid
            station = self.stations[station_id].geoid

            return SimulationState._same_geoid(vehicle, station, self.sim_h3_resolution, override_resolution)

    def vehicle_at_base(self,
                        vehicle_id: VehicleId,
                        base_id: BaseId,
                        override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution
        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param base_id: the base we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif base_id not in self.bases:
            return SimulationStateError(f"station {base_id} not in this simulation")
        else:
            vehicle = self.vehicles[vehicle_id].geoid
            base = self.bases[base_id].geoid

            return SimulationState._same_geoid(vehicle, base, self.sim_h3_resolution, override_resolution)

    def board_vehicle(self,
                      request_id: RequestId,
                      vehicle_id: VehicleId) -> Union[SimulationStateError, SimulationState]:
        """
        places passengers from a request into a Vehicle
        :param request_id: the request that will board the vehicle; removes the request from the simulation
        :param vehicle_id:
        :return: updated simulation state, or an error. vehicle position is idempotent.
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(
                f"request {request_id} attempting to board vehicle {vehicle_id} which does not exist")
        elif request_id not in self.requests:
            return SimulationStateError(
                f"request {request_id} does not exist but is attempting to board vehicle {vehicle_id}")
        else:
            vehicle = self.vehicles[vehicle_id]
            request = self.requests[request_id]
            updated_vehicle = vehicle.add_passengers(request.passengers)

            updated_vehicles = copy(self.vehicles)
            updated_vehicles.update([(vehicle_id, updated_vehicle)])

            return self._replace(
                vehicles=updated_vehicles,
            ).remove_request(request_id)
