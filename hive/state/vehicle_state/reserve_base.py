from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId, BaseId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class ReserveBase(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    base_id: BaseId

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, base_id: BaseId) -> ReserveBase:
        return cls(vehicle_id, base_id, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.RESERVE_BASE

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        to enter this state, the base must have a stall for the vehicle

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, an updated SimulationState, or (None, None) when the base has no stalls
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        base = sim.bases.get(self.base_id)
        context = f"vehicle {self.vehicle_id} entering reserve base at base {self.base_id}"
        if not vehicle:
            return SimulationStateError(f"{context}; vehicle not found"), None
        elif not base:
            return SimulationStateError(f"{context}; base not found"), None
        elif base.geoid != vehicle.geoid:
            log.warning(
                f"ReserveBase.enter(): vehicle {vehicle.id} not at same location as {base.id}")
            return None, None
        elif not base.membership.grant_access_to_membership(vehicle.membership):
            msg = f"ReserveBase.enter(): vehicle {vehicle.id} does not have access to base {base.id}"
            return SimulationStateError(msg), None

        else:
            updated_base = base.checkout_stall()
            if not updated_base:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_base(sim, updated_base)
                if error:
                    response = SimulationStateError(
                        f"failure during ReserveBase.enter for vehicle {self.vehicle_id}")
                    response.__cause__ = error
                    return response, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        releases the stall that this vehicle occupied

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, or an updated sim
        """
        base = sim.bases.get(self.base_id)
        context = f"vehicle {self.vehicle_id} exiting reserve base at base {self.base_id}"
        if not base:
            return SimulationStateError(f"{context}; base not found"), None
        else:
            error, updated_base = base.return_stall()
            if error:
                response = SimulationStateError(
                    f"failure during ReserveBase.exit for vehicle {self.vehicle_id}")
                response.__cause__ = error
                return response, None
            return simulation_state_ops.modify_base(sim, updated_base)

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        There is no terminal state for ReserveBase

        :param sim: the sim state
        :param env: the sim environment
        :return: False
        """
        return False

    def _default_terminal_state(
            self, sim: SimulationState,
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        return None, self

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        as of now, there is no update for being ReserveBase

        :param sim: the simulation state
        :param env: the simulation environment
        :return: NOOP
        """
        return None, sim
