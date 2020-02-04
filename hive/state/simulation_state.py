from __future__ import annotations

import functools as ft
from typing import NamedTuple, Optional, Union, cast, Tuple, TYPE_CHECKING

import immutables
from h3 import h3

from hive.model.vehiclestate import VehicleState, VehicleStateCategory
from hive.state.at_location_response import AtLocationResponse
from hive.state.terminal_state_effect_ops import TerminalStateEffectOps, TerminalStateEffectArgs
from hive.util.exception import *
from hive.util.helpers import DictOps
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.base import Base
from hive.model.request import Request
from hive.util.typealiases import RequestId, VehicleId, BaseId, StationId, SimTime, GeoId

if TYPE_CHECKING:
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.runner.environment import Environment
    from hive.util.units import Seconds


class SimulationState(NamedTuple):
    """
    resolution of '11' is within 25 meters/82 feet. this decides how granular
    the simulation will operate for internal operations. the user can still
    specify their own level of granularity for
    https://uber.github.io/h3/#/documentation/core-library/resolution-table
    """
    # road network representation
    road_network: RoadNetwork

    # simulation parameters
    sim_time: SimTime
    sim_timestep_duration_seconds: Seconds
    sim_h3_location_resolution: int
    sim_h3_search_resolution: int

    # objects of the simulation
    stations: immutables.Map[StationId, Station] = immutables.Map()
    bases: immutables.Map[BaseId, Base] = immutables.Map()
    vehicles: immutables.Map[VehicleId, Vehicle] = immutables.Map()
    requests: immutables.Map[RequestId, Request] = immutables.Map()

    # location collections - the lowest-level spatial representation in Hive
    v_locations: immutables.Map[GeoId, Tuple[VehicleId, ...]] = immutables.Map()
    r_locations: immutables.Map[GeoId, Tuple[RequestId, ...]] = immutables.Map()
    s_locations: immutables.Map[GeoId, Tuple[StationId, ...]] = immutables.Map()
    b_locations: immutables.Map[GeoId, Tuple[BaseId, ...]] = immutables.Map()

    # search collections   - a higher-level spatial representation used for ring search
    v_search: immutables.Map[GeoId, Tuple[VehicleId, ...]] = immutables.Map()
    r_search: immutables.Map[GeoId, Tuple[RequestId, ...]] = immutables.Map()
    s_search: immutables.Map[GeoId, Tuple[StationId, ...]] = immutables.Map()
    b_search: immutables.Map[GeoId, Tuple[BaseId, ...]] = immutables.Map()

    def add_request(self, request: Request) -> Union[Exception, SimulationState]:
        """
        adds a request to the SimulationState

        :param request: the request to add
        :return: the updated simulation state, or an error
        """
        if not isinstance(request, Request):
            return TypeError(f"sim.add_request requires a request but received a {type(request)}")
        elif not self.road_network.geoid_within_geofence(request.origin):
            return SimulationStateError(f"origin {request.origin} not within road network geofence")
        elif not self.road_network.geoid_within_simulation(request.destination):
            return SimulationStateError(f"destination {request.destination} not within entire road network")
        search_geoid = h3.h3_to_parent(request.geoid, self.sim_h3_search_resolution)
        return self._replace(
            requests=DictOps.add_to_dict(self.requests, request.id, request),
            r_locations=DictOps.add_to_location_dict(self.r_locations, request.geoid, request.id),
            r_search=DictOps.add_to_location_dict(self.r_search, search_geoid, request.id)
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
        request = self.requests[request_id]
        search_geoid = h3.h3_to_parent(request.geoid, self.sim_h3_search_resolution)
        updated_requests = DictOps.remove_from_dict(self.requests, request.id)
        updated_r_locations = DictOps.remove_from_location_dict(self.r_locations, request.geoid, request.id)
        updated_r_search = DictOps.remove_from_location_dict(self.r_search, search_geoid, request.id)

        return self._replace(
            requests=updated_requests,
            r_locations=updated_r_locations,
            r_search=updated_r_search
        )

    def modify_request(self, updated_request: Request) -> Union[Exception, SimulationState]:
        """
        given an updated request, update the SimulationState with that request
        :param updated_request:
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_request, Request):
            return TypeError(f"sim.update_request requires a request but received {type(updated_request)}")

        result = DictOps.update_entity_dictionaries(updated_request,
                                                    self.requests,
                                                    self.r_locations,
                                                    self.r_search,
                                                    self.sim_h3_search_resolution)

        return self._replace(
            requests=result.entities if result.entities else self.requests,
            r_locations=result.locations if result.locations else self.r_locations,
            r_search=result.search if result.search else self.r_search
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

        search_geoid = h3.h3_to_parent(vehicle.geoid, self.sim_h3_search_resolution)
        updated_v_locations = DictOps.add_to_location_dict(self.v_locations, vehicle.geoid, vehicle.id)
        updated_v_search = DictOps.add_to_location_dict(self.v_search, search_geoid, vehicle.id)
        return self._replace(
            vehicles=DictOps.add_to_dict(self.vehicles, vehicle.id, vehicle),
            v_locations=updated_v_locations,
            v_search=updated_v_search
        )

    def modify_vehicle(self, updated_vehicle: Vehicle) -> Union[Exception, SimulationState]:
        """
        given an updated vehicle, update the SimulationState with that vehicle

        :param updated_vehicle: the vehicle after calling a transition function and .step()
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_vehicle, Vehicle):
            return TypeError(f"sim.update_vehicle requires a vehicle but received {type(updated_vehicle)}")
        elif not self.road_network.geoid_within_geofence(updated_vehicle.geoid):
            return SimulationStateError(f"cannot add vehicle {updated_vehicle.id} to sim: not within road network")

        result = DictOps.update_entity_dictionaries(updated_vehicle,
                                                    self.vehicles,
                                                    self.v_locations,
                                                    self.v_search,
                                                    self.sim_h3_search_resolution)

        return self._replace(
            vehicles=result.entities if result.entities else self.vehicles,
            v_locations=result.locations if result.locations else self.v_locations,
            v_search=result.search if result.search else self.v_search
        )

    def step_vehicle(self, vehicle_id: VehicleId, env: Environment) -> SimulationState:
        """
        Steps a vehicle in time, checking for arrival at a terminal state condition.

        :param vehicle_id: The id of the vehicle to step
        :param env: provides powertrain/powercurve models
        :return: An update simulation state
        """
        if not isinstance(vehicle_id, VehicleId):
            raise TypeError(f"remove_request() takes a VehicleId (str), not a {type(vehicle_id)}")
        if vehicle_id not in self.vehicles:
            raise SimulationStateError(f"attempting to update vehicle {vehicle_id} which is not in simulation")

        # Handle terminal state instant effects.
        vehicle = self.vehicles[vehicle_id]
        effect_args = TerminalStateEffectArgs(self, vehicle_id)
        sim_state_w_effects: SimulationState = TerminalStateEffectOps.switch(vehicle.vehicle_state, effect_args)

        # Apply time based effects.
        vehicle = sim_state_w_effects.vehicles[vehicle_id]
        if VehicleStateCategory.from_vehicle_state(vehicle.vehicle_state) == VehicleStateCategory.MOVE:
            # perform a move event
            powertrain = env.powertrains[vehicle.powertrain_id]
            updated_vehicle = vehicle.move(sim_state_w_effects.road_network,
                                           powertrain,
                                           sim_state_w_effects.sim_timestep_duration_seconds)

            return sim_state_w_effects.modify_vehicle(updated_vehicle)

        elif VehicleStateCategory.from_vehicle_state(vehicle.vehicle_state) == VehicleStateCategory.CHARGE:
            # perform a charge event
            powercurve = env.powercurves[vehicle.powercurve_id]
            stations_at_location = sim_state_w_effects.at_geoid(vehicle.geoid).get('stations')
            station = sim_state_w_effects.stations[stations_at_location[0]] if stations_at_location else None
            charged_vehicle = vehicle.charge(powercurve, sim_state_w_effects.sim_timestep_duration_seconds)

            # determine price of charge event
            kwh_transacted = (charged_vehicle.energy_source.energy_kwh - vehicle.energy_source.energy_kwh)  # kwh
            charger_price = station.charger_prices.get(charged_vehicle.charger_intent)  # Currency
            charging_price = kwh_transacted * charger_price if charger_price else 0.0

            # update currency balance for vehicle, station
            updated_vehicle = charged_vehicle.send_payment(charging_price)
            updated_station = station.receive_payment(charging_price)

            return sim_state_w_effects.modify_vehicle(updated_vehicle).modify_station(updated_station)

        elif vehicle.vehicle_state == VehicleState.IDLE:
            # perform an idle event
            updated_vehicle = vehicle.idle(sim_state_w_effects.sim_timestep_duration_seconds)

            return sim_state_w_effects.modify_vehicle(updated_vehicle)

        else:
            # reserve base - noop
            return sim_state_w_effects

    def step_simulation(self, env: Environment) -> SimulationState:
        """
        advances this simulation

        :return: the simulation after calling step_vehicle() on all vehicles
        """
        next_state = ft.reduce(
            lambda acc, v_id: acc.step_vehicle(v_id, env),
            self.vehicles.keys(),
            self
        )

        return next_state._replace(
            sim_time=self.sim_time + self.sim_timestep_duration_seconds
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

        vehicle = self.vehicles[vehicle_id]
        search_geoid = h3.h3_to_parent(vehicle.geoid, self.sim_h3_search_resolution)

        return self._replace(
            vehicles=DictOps.remove_from_dict(self.vehicles, vehicle_id),
            v_locations=DictOps.remove_from_location_dict(self.v_locations, vehicle.geoid, vehicle_id),
            v_search=DictOps.remove_from_location_dict(self.v_search, search_geoid, vehicle_id)
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

        search_geoid = h3.h3_to_parent(station.geoid, self.sim_h3_search_resolution)
        return self._replace(
            stations=DictOps.add_to_dict(self.stations, station.id, station),
            s_locations=DictOps.add_to_location_dict(self.s_locations, station.geoid, station.id),
            s_search=DictOps.add_to_location_dict(self.s_search, search_geoid, station.id)
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

        station = self.stations[station_id]
        search_geoid = h3.h3_to_parent(station.geoid, self.sim_h3_search_resolution)

        return self._replace(
            stations=DictOps.remove_from_dict(self.stations, station_id),
            s_locations=DictOps.remove_from_location_dict(self.s_locations, station.geoid, station_id),
            s_search=DictOps.remove_from_location_dict(self.s_search, search_geoid, station_id)
        )

    def modify_station(self, updated_station: Station) -> Union[Exception, SimulationState]:
        """
        given an updated station, update the SimulationState with that station
        invariant: locations will not be changed!
        :param updated_station:
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_station, Station):
            return TypeError(f"sim.update_station requires a station but received {type(updated_station)}")

        return self._replace(
            stations=DictOps.add_to_dict(self.stations, updated_station.id, updated_station)
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

        search_geoid = h3.h3_to_parent(base.geoid, self.sim_h3_search_resolution)
        return self._replace(
            bases=DictOps.add_to_dict(self.bases, base.id, base),
            b_locations=DictOps.add_to_location_dict(self.b_locations, base.geoid, base.id),
            b_search=DictOps.add_to_location_dict(self.b_search, search_geoid, base.id)
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

        base = self.bases[base_id]
        search_geoid = h3.h3_to_parent(base.geoid, self.sim_h3_search_resolution)

        return self._replace(
            bases=DictOps.remove_from_dict(self.bases, base_id),
            b_locations=DictOps.remove_from_location_dict(self.b_locations, base.geoid, base_id),
            b_search=DictOps.remove_from_location_dict(self.b_search, search_geoid, base_id)
        )

    def modify_base(self, updated_base: Base) -> Union[Exception, SimulationState]:
        """
        given an updated base, update the SimulationState with that base
        invariant: base locations will not be changed!
        :param updated_base:
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_base, Base):
            return TypeError(f"sim.update_base requires a base but received {type(updated_base)}")

        return self._replace(
            bases=DictOps.add_to_dict(self.bases, updated_base.id, updated_base)
        )

    def update_road_network(self, sim_time: SimTime) -> SimulationState:
        """
        trigger the update of the road network model based on the current sim time

        :param sim_time: the current sim time
        :return: updated simulation state (and road network)
        """
        return self._replace(
            road_network=self.road_network.update(sim_time)
        )

    def at_geoid(self, geoid: GeoId) -> AtLocationResponse:
        """
        returns a dictionary with the list of ids found at this location for all entities
        :param geoid: geoid to look up, should be at the self.sim_h3_location_resolution
        :return: an Optional AtLocationResponse
        """
        if not isinstance(geoid, GeoId):
            raise TypeError(f"sim.update_vehicle requires a vehicle but received {type(geoid)}")

        vehicles = self.v_locations[geoid] if geoid in self.v_locations else ()
        requests = self.r_locations[geoid] if geoid in self.r_locations else ()
        stations = self.s_locations[geoid] if geoid in self.s_locations else ()
        bases = self.b_locations[geoid] if geoid in self.b_locations else ()

        result = cast(AtLocationResponse, {
            'vehicles': vehicles,
            'requests': requests,
            'stations': stations,
            'bases': bases
        })
        return result

    def vehicle_at_request(self,
                           vehicle_id: VehicleId,
                           request_id: RequestId,
                           override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param request_id: the request we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif request_id not in self.requests:
            return SimulationStateError(f"request {request_id} not in this simulation")

        vehicle = self.vehicles[vehicle_id].geoid
        request = self.requests[request_id].origin

        return SimulationState._same_geoid(vehicle, request, self.sim_h3_location_resolution, override_resolution)

    def vehicle_at_station(self,
                           vehicle_id: VehicleId,
                           station_id: StationId,
                           override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the station within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param station_id: the station we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif station_id not in self.stations:
            return SimulationStateError(f"station {station_id} not in this simulation")
        else:
            vehicle = self.vehicles[vehicle_id].geoid
            station = self.stations[station_id].geoid

            return SimulationState._same_geoid(vehicle, station, self.sim_h3_location_resolution, override_resolution)

    def vehicle_at_base(self,
                        vehicle_id: VehicleId,
                        base_id: BaseId,
                        override_resolution: Optional[int] = None) -> Union[SimulationStateError, bool]:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param base_id: the base we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif base_id not in self.bases:
            return SimulationStateError(f"station {base_id} not in this simulation")

        vehicle = self.vehicles[vehicle_id].geoid
        base = self.bases[base_id].geoid

        return SimulationState._same_geoid(vehicle, base, self.sim_h3_location_resolution, override_resolution)

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

        vehicle = self.vehicles[vehicle_id]
        request = self.requests[request_id]
        updated_vehicle = vehicle.add_passengers(request.passengers).receive_payment(request.value)

        updated_vehicles = self.vehicles.set(vehicle_id, updated_vehicle)
        # updated_vehicles = copy(self.vehicles)
        # updated_vehicles.update([(vehicle_id, updated_vehicle)])

        return self._replace(
            vehicles=updated_vehicles,
        ).remove_request(request_id)

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

        a_parent = h3.h3_to_parent(a, override_resolution)
        b_parent = h3.h3_to_parent(b, override_resolution)
        return a_parent == b_parent
