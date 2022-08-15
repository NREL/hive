from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.runner.environment import Environment
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.state.vehicle_state import vehicle_state_ops
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, VehicleId, ChargerId

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState


class DispatchStation(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    station_id: StationId
    route: Route
    charger_id: ChargerId

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, station_id: StationId, route: Route,
              charger_id: ChargerId) -> DispatchStation:
        return DispatchStation(vehicle_id=vehicle_id,
                               station_id=station_id,
                               charger_id=charger_id,
                               route=route,
                               instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.DISPATCH_STATION
    
    def update_route(self, route: Route) -> DispatchStation:
        return self._replace(route=route)

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        station = sim.stations.get(self.station_id)
        vehicle = sim.vehicles.get(self.vehicle_id)
        is_valid = route_cooresponds_with_entities(
            self.route, vehicle.position, station.position) if vehicle and station else False
        context = f"vehicle {self.vehicle_id} entering dispatch station state for station {self.station_id} with charger {self.charger_id}"
        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not station:
            return SimulationStateError(f"station not found; context: {context}"), None
        elif station.geoid == vehicle.geoid:
            # already there!
            next_state = ChargingStation.build(self.vehicle_id, self.station_id, self.charger_id)
            return next_state.enter(sim, env)
        elif not is_valid:
            return None, None
        elif not station.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} and station {station.id} don't share a membership"
            return SimulationStateError(msg), None
        else:
            result = VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)
            return result

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a station

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the station
        """
        return len(self.route) == 0

    def _default_terminal_state(
            self, sim: SimulationState,
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        available_chargers = station.get_available_chargers(self.charger_id) if station else None
        context = f"vehicle {self.vehicle_id} entering default terminal state for dispatch station state for station {self.station_id} with charger {self.charger_id}"
        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not station:
            return SimulationStateError(f"station not found; context: {context}"), None
        elif station.geoid != vehicle.geoid:
            locations = f"{station.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to station {self.station_id} but locations do not match: {locations}"
            return SimulationStateError(message), None
        else:
            next_state = ChargingStation.build(
                self.vehicle_id, self.station_id,
                self.charger_id) if available_chargers is not None else ChargeQueueing.build(
                    self.vehicle_id, self.station_id, self.charger_id, sim.sim_time)
            return None, next_state

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the station

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        move_error, move_sim = vehicle_state_ops.move(sim, env, self.vehicle_id)

        if move_error:
            response = SimulationStateError(
                f"failure during DispatchStation._perform_update for vehicle {self.vehicle_id}")
            response.__cause__ = move_error
            return response, None
        else:
            return None, move_sim
