from __future__ import annotations

import functools as ft
from copy import copy
from typing import NamedTuple, Dict, Optional, Union, cast

from h3 import h3

from hive.dispatcher.instruction import Instruction
from hive.model.base import Base
from hive.model.energy.charger import Charger
from hive.model.request import Request
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.vehiclestate import VehicleState, VehicleStateCategory
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.energy.powertrain import Powertrain
from hive.model.energy.powercurve import Powercurve
from hive.state.at_location_response import AtLocationResponse
from hive.state.terminal_state_effect_ops import TerminalStateEffectOps, TerminalStateEffectArgs
from hive.state.vehicle_terminal_effect_ops import VehicleTransitionEffectOps, \
    VehicleTransitionEffectArgs
from hive.util.exception import *
from hive.util.helpers import DictOps
from hive.util.typealiases import *
from hive.util.units import s


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
    sim_timestep_duration_seconds: SimTime
    sim_h3_resolution: int

    # objects of the simulation
    stations: Dict[StationId, Station] = {}
    bases: Dict[BaseId, Base] = {}
    vehicles: Dict[VehicleId, Vehicle] = {}
    requests: Dict[RequestId, Request] = {}
    powertrains: Dict[PowertrainId, Powertrain] = {}
    powercurves: Dict[PowercurveId, Powercurve] = {}

    # location lookup collections
    v_locations: Dict[GeoId, Tuple[VehicleId, ...]] = {}
    r_locations: Dict[GeoId, Tuple[RequestId, ...]] = {}
    s_locations: Dict[GeoId, Tuple[StationId, ...]] = {}
    b_locations: Dict[GeoId, Tuple[BaseId, ...]] = {}

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
        else:
            return self._replace(
                requests=DictOps.add_to_entity_dict(self.requests, request.id, request),
                r_locations=DictOps.add_to_location_dict(self.r_locations, request.origin, request.id)
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
            return self._replace(
                requests=DictOps.remove_from_entity_dict(self.requests, request.id),
                r_locations=DictOps.remove_from_location_dict(self.r_locations, request.origin, request.id)
            )

    # TODO: Think about making this generic wrt entities.
    def modify_request(self, updated_request: Request) -> Union[Exception, SimulationState]:
        """
        given an updated request, update the SimulationState with that request 
        :param updated_request: 
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_request, Request):
            return TypeError(f"sim.update_request requires a request but received {type(updated_request)}")
        else:

            old_request = self.requests[updated_request.id]

            if old_request.origin == updated_request.origin:
                return self._replace(
                    requests=DictOps.add_to_entity_dict(self.requests, updated_request.id, updated_request)
                )
            else:

                # unset from old geoid add add to new one
                r_locations_removed = DictOps.remove_from_location_dict(self.r_locations,
                                                                        old_request.origin,
                                                                        old_request.id)
                r_locations_updated = DictOps.add_to_location_dict(r_locations_removed,
                                                                   updated_request.origin,
                                                                   updated_request.id)

                return self._replace(
                    requests=DictOps.add_to_entity_dict(self.requests, updated_request.id, updated_request),
                    r_locations=r_locations_updated
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
            return self._replace(
                vehicles=DictOps.add_to_entity_dict(self.vehicles, vehicle.id, vehicle),
                v_locations=DictOps.add_to_location_dict(self.v_locations, vehicle.geoid, vehicle.id)
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
        else:

            old_vehicle = self.vehicles[updated_vehicle.id]

            if old_vehicle.geoid == updated_vehicle.geoid:
                return self._replace(
                    vehicles=DictOps.add_to_entity_dict(self.vehicles, updated_vehicle.id, updated_vehicle)
                )
            else:

                # unset from old geoid add add to new one
                v_locations_removed = DictOps.remove_from_location_dict(self.v_locations,
                                                                        old_vehicle.geoid,
                                                                        old_vehicle.id)
                v_locations_updated = DictOps.add_to_location_dict(v_locations_removed,
                                                                   updated_vehicle.geoid,
                                                                   updated_vehicle.id)

                return self._replace(
                    vehicles=DictOps.add_to_entity_dict(self.vehicles, updated_vehicle.id, updated_vehicle),
                    v_locations=v_locations_updated
                )

    def apply_instruction(self, i: Instruction) -> Optional[SimulationState]:
        """
        test if vehicle transition is valid, and if so, apply it, resolving any externalities in the process
        :param i: the instruction to apply
        :return: the updated simulation state or an exception on failure
        """
        if not isinstance(i, Instruction):
            raise TypeError(f"remove_request() takes a VehicleId (str), not a {type(i.vehicle_id)}")
        if i.vehicle_id not in self.vehicles:
            raise SimulationStateError(f"attempting to update vehicle {i.vehicle_id} which is not in simulation")

        vehicle = self.vehicles[i.vehicle_id]
        if not vehicle.can_transition(i.action):
            return None
        else:
            # apply instruction to vehicle
            updated_vehicle = vehicle.transition(i.action)
            updated_vehicle_sim_state = self.modify_vehicle(updated_vehicle)

            # Handle instantaneous effects
            effect_args = VehicleTransitionEffectArgs(updated_vehicle_sim_state, i)
            updated_sim_state = VehicleTransitionEffectOps.switch(i.action, effect_args)

            return updated_sim_state

    def step_vehicle(self, vehicle_id: VehicleId) -> SimulationState:
        if not isinstance(vehicle_id, VehicleId):
            raise TypeError(f"remove_request() takes a VehicleId (str), not a {type(vehicle_id)}")
        if vehicle_id not in self.vehicles:
            raise SimulationStateError(f"attempting to update vehicle {vehicle_id} which is not in simulation")

        # Handle terminal state instant effects.
        vehicle = self.vehicles[vehicle_id]
        effect_args = TerminalStateEffectArgs(self, vehicle_id)
        sim_state_w_effects = TerminalStateEffectOps.switch(vehicle.vehicle_state, effect_args)

        # Apply time based effects.
        vehicle = sim_state_w_effects.vehicles[vehicle_id]
        if VehicleStateCategory.from_vehicle_state(vehicle.vehicle_state) == VehicleStateCategory.MOVE:
            powertrain = sim_state_w_effects.powertrains[vehicle.powertrain_id]
            vehicle = vehicle.move(sim_state_w_effects.road_network,
                                   powertrain,
                                   sim_state_w_effects.sim_timestep_duration_seconds)
        elif VehicleStateCategory.from_vehicle_state(vehicle.vehicle_state) == VehicleStateCategory.CHARGE:
            powercurve = sim_state_w_effects.powercurves[vehicle.powercurve_id]
            vehicle = vehicle.charge(powercurve, sim_state_w_effects.sim_timestep_duration_seconds)
        elif vehicle.vehicle_state == VehicleState.IDLE:
            vehicle = vehicle.idle(sim_state_w_effects.sim_timestep_duration_seconds)

        updated_sim_state = sim_state_w_effects.modify_vehicle(vehicle)

        return updated_sim_state

    def step_simulation(self) -> SimulationState:
        """
        advances this simulation
        :return: the simulation after calling step() on all vehicles
        """
        next_state = ft.reduce(
            lambda acc, v_id: acc.step_vehicle(v_id),
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
        else:
            vehicle = self.vehicles[vehicle_id]

            return self._replace(
                vehicles=DictOps.remove_from_entity_dict(self.vehicles, vehicle_id),
                v_locations=DictOps.remove_from_location_dict(self.v_locations, vehicle.geoid, vehicle_id)
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
            return self._replace(
                stations=DictOps.add_to_entity_dict(self.stations, station.id, station),
                s_locations=DictOps.add_to_location_dict(self.s_locations, station.geoid, station.id)
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

            return self._replace(
                stations=DictOps.remove_from_entity_dict(self.stations, station_id),
                s_locations=DictOps.remove_from_location_dict(self.s_locations, station.geoid, station_id)
            )

    def modify_station(self, updated_station: Station) -> Union[Exception, SimulationState]:
        """
        given an updated station, update the SimulationState with that station
        :param updated_station:
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_station, Station):
            return TypeError(f"sim.update_station requires a station but received {type(updated_station)}")
        else:
            return self._replace(
                stations=DictOps.add_to_entity_dict(self.stations, updated_station.id, updated_station)
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
            return self._replace(
                bases=DictOps.add_to_entity_dict(self.bases, base.id, base),
                b_locations=DictOps.add_to_location_dict(self.b_locations, base.geoid, base.id)
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

            return self._replace(
                bases=DictOps.remove_from_entity_dict(self.bases, base_id),
                b_locations=DictOps.remove_from_location_dict(self.b_locations, base.geoid, base_id)
            )

    def modify_base(self, updated_base: Base) -> Union[Exception, SimulationState]:
        """
        given an updated base, update the SimulationState with that base
        :param updated_base:
        :return: the updated simulation, or an error
        """
        if not isinstance(updated_base, Base):
            return TypeError(f"sim.update_base requires a base but received {type(updated_base)}")
        else:
            return self._replace(
                bases=DictOps.add_to_entity_dict(self.bases, updated_base.id, updated_base)
            )

    def add_powertrain(self, powertrain: Powertrain) -> Union[Exception, SimulationState]:
        """
        Adds a powertrain to the simulation
        :param powertrain: 
        :return: 
        """
        if not isinstance(powertrain, Powertrain):
            return TypeError(f"sim.add_base requires a base but received {type(powertrain)}")
        else:
            return self._replace(
                powertrains=DictOps.add_to_entity_dict(self.powertrains, powertrain.get_id(), powertrain),
            )

    def add_powercurve(self, powercurve: Powercurve) -> Union[Exception, SimulationState]:
        """
        Adds a powercurve to the simulation
        :param powercurve: 
        :return: 
        """
        if not isinstance(powercurve, Powercurve):
            return TypeError(f"sim.add_base requires a base but received {type(powercurve)}")
        else:
            return self._replace(
                powercurves=DictOps.add_to_entity_dict(self.powercurves, powercurve.get_id(), powercurve),
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

    def at_geoid(self, geoid: GeoId) -> Union[Exception, AtLocationResponse]:
        """
        returns a dictionary with the list of ids found at this location for all entities
        :param geoid: geoid to look up
        :return: an Optional AtLocationResponse
        """
        if not isinstance(geoid, GeoId):
            return TypeError(f"sim.update_vehicle requires a vehicle but received {type(geoid)}")
        else:
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
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_resolution
        :return: bool
        """
        if vehicle_id not in self.vehicles:
            return SimulationStateError(f"vehicle {vehicle_id} not in this simulation")
        elif request_id not in self.requests:
            return SimulationStateError(f"request {request_id} not in this simulation")
        else:
            vehicle = self.vehicles[vehicle_id].geoid
            request = self.requests[request_id].origin

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
