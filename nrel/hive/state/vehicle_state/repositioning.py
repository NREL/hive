from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from nrel.hive.model.roadnetwork.route import (
    Route,
    route_cooresponds_with_entities,
)
from nrel.hive.runner.environment import Environment
from nrel.hive.state.vehicle_state import vehicle_state_ops
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.vehicle_state import (
    VehicleState,
    VehicleStateInstanceId,
)
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.exception import SimulationStateError
from nrel.hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState


@dataclass(frozen=True)
class Repositioning(VehicleState):
    vehicle_id: VehicleId
    route: Route

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, route: Route) -> Repositioning:
        """
        build a repositioning state

        :param vehicle_id: the vehicle id
        :param route: the route to the new location
        :return: a repositioning state
        """
        return cls(vehicle_id=vehicle_id, route=route, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.REPOSITIONING

    def update_route(self, route: Route) -> Repositioning:
        return replace(self, route=route)

    def update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim.vehicles.get(self.vehicle_id)
        is_valid = (
            route_cooresponds_with_entities(self.route, vehicle.position) if vehicle else False
        )
        context = f"vehicle {self.vehicle_id} entering repositioning state"
        if not vehicle:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        elif not is_valid:
            return None, None
        else:
            result = VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)
            return result

    def exit(
        self, next_state: VehicleState, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        next_state = Idle.build(self.vehicle_id)
        return None, next_state

    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the repositioning location

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        move_error, move_sim = vehicle_state_ops.move(sim, env, self.vehicle_id)

        if move_error:
            response = SimulationStateError(
                f"failure during Repositioning._perform_update for vehicle {self.vehicle_id}"
            )
            response.__cause__ = move_error
            return response, None
        else:
            return None, move_sim
