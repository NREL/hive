import logging
from typing import NamedTuple, Tuple, Optional

from hive.model.passenger import Passenger
from hive.model.roadnetwork.route import Route, valid_route
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import pick_up_trip, move
from hive.util.exception import SimulationStateError
from hive.util.typealiases import RequestId, VehicleId

log = logging.getLogger(__name__)


class ServicingTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    request_id: RequestId
    route: Route
    passengers: Tuple[Passenger, ...]

    def update(self,
               sim: 'SimulationState',
               env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self,
              sim: 'SimulationState',
              env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        if not request:
            # request was already picked up
            return None, None
        elif request and request.geoid != vehicle.geoid:
            locations = f"{request.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to request {self.request_id} but locations do not match: {locations}"
            return SimulationStateError(message), None
        elif not vehicle.membership.valid_membership(request.membership):
            log.debug(f"vehicle {vehicle.id} and request {request.id} don't share a membership")
            return None, None
        else:
            route_is_valid = valid_route(self.route, request.origin, request.destination)
            # request exists: pick up the trip and enter a ServicingTrip state
            pickup_error, pickup_sim = pick_up_trip(sim, env, self.vehicle_id, self.request_id)
            if not route_is_valid:
                return None, None
            elif pickup_error:
                return pickup_error, None
            else:
                return VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id, self)

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        handles the dropping off of passengers

        :param sim: the sim state

        :param env: the sim environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if still serving the trip
        """

        # todo: log the completion of a trip

        vehicle = sim.vehicles.get(self.vehicle_id)
        soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(vehicle) if vehicle else 0
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif soc == 0:
            # vehicle is out of fuel, can transition to support ServicingTrip -> OutOfService
            # todo: allow penalty due to stranded passengers
            return None, sim
        elif len(self.route) != 0:
            # cannot exit when not at passenger's destination
            return None, None
        elif len(self.passengers) == 0:
            # unlikely edge case that there were no passengers?
            return None, sim
        else:
            # confirm each passenger has reached their destination
            for passenger in self.passengers:
                if passenger.destination != vehicle.geoid:
                    locations = f"{passenger.destination} != {vehicle.geoid}"
                    message = f"vehicle {self.vehicle_id} dropping off passenger {passenger.id} but location is wrong: {locations}"
                    return SimulationStateError(message), None
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state

        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        by default, transition to ReserveBase if there are stalls, otherwise, Idle

        :param sim: the sim state

        :param env: the sim environment
        :return: an exception due to failure or an optional updated simulation
        """

        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        take a step along the route to the base

        :param sim: the simulation state

        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, move_result.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            return simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)
