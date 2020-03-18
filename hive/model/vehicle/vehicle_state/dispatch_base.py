from typing import NamedTuple, Tuple, Optional

from hive.model.vehicle.vehicle_state import vehicle_state_ops
from hive.util.exception import SimulationStateError

from hive.model.roadnetwork.route import Route

from hive.util.typealiases import BaseId, VehicleId

from hive import SimulationState, Environment
from hive.model.vehicle.vehicle_state.vehicle_state import VehicleState


class DispatchBase(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    base_id: BaseId
    route: Route

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        pass

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        pass

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _default_terminal_state_transition(self,
                                           sim: SimulationState,
                                           env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        by default, transition to ReserveBase if there are stalls, otherwise, Idle
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        bases = sim.at_geoid(vehicle.geoid).get("bases")
        base = bases[0] if bases else None
        if not base:
            msg = f"terminating a DispatchBase state but not at the location of base {self.base_id}"
            return SimulationStateError(msg), None
        elif base.available_stalls > 0:
            # transition into ReserveBase
            next_state = ReserveBase(self.vehicle_id)
            return next_state.enter(sim, env)
        else:
            # transition into Idle
            next_state = Idle(self.vehicle_id)
            return next_state.enter(sim, env)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the base
        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """


        errors, updated_sim = vehicle_state_ops.move()
        # updated_vehicle = less_energy_vehicle.transition(
        #     VehicleState.OUT_OF_SERVICE) if updated_energy_source.is_empty() else less_energy_vehicle