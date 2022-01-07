from __future__ import annotations
import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.runner.environment import Environment
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state import vehicle_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import BaseId, VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class DispatchBase(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    base_id: BaseId
    route: Route

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, base_id: BaseId, route: Route) -> DispatchBase:
        return cls(vehicle_id=vehicle_id, base_id=base_id, route=route, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.DISPATCH_BASE
    
    def update_route(self, route: Route) -> DispatchBase:
        return self._replace(route=route)

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        base = sim.bases.get(self.base_id)
        vehicle = sim.vehicles.get(self.vehicle_id)
        is_valid = route_cooresponds_with_entities(self.route, vehicle.position,
                                                   base.position) if vehicle and base else False
        context = f"vehicle {self.vehicle_id} entering dispatch base state at base {self.base_id}"
        if not base:
            msg = f"base not found; context: {context}"
            return SimulationStateError(msg), None
        elif not vehicle:
            msg = f"vehicle not found; context {context}"
            return SimulationStateError(msg), None
        elif not is_valid:
            return None, None
        elif not base.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} and base {base.id} don't share a membership"
            return SimulationStateError(msg), None
        else:
            result = VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)
            return result

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
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
        base = sim.bases.get(self.base_id)
        context = f"vehicle {self.vehicle_id} entering terminal state for dispatch base at {self.base_id}"
        if not base:
            msg = f"base not found; context: {context}"
            return SimulationStateError(msg), None
        elif base.geoid != vehicle.geoid:
            locations = f"{base.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to base {self.base_id} but locations do not match: {locations}"
            return SimulationStateError(message), None
        else:
            if base.available_stalls > 0:
                next_state = ReserveBase.build(self.vehicle_id, self.base_id)
            else:
                next_state = Idle.build(self.vehicle_id)
            return None, next_state

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        move_error, move_sim = vehicle_state_ops.move(sim, env, self.vehicle_id)

        if move_error:
            response = SimulationStateError(
                f"failure during DispatchBase._perform_update for vehicle {self.vehicle_id}")
            response.__cause__ = move_error
            return response, None
        else:
            return None, move_sim
