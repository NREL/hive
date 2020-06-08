from typing import NamedTuple, Tuple, Optional

from hive.model.energy.charger import Charger
from hive.model.roadnetwork.route import Route, valid_route
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, VehicleId, ChargerId


class DispatchStation(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    station_id: StationId
    route: Route
    charger_id: ChargerId

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        station = sim.stations.get(self.station_id)
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            route_is_valid = valid_route(self.route, vehicle.geoid, station.geoid)
            if not route_is_valid:
                return None, None
            else:
                return VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        this terminates when we reach a station
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the station
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        by default, transition into a ChargingStation event, but if not possible, then Idle
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        available_chargers = station.available_chargers.get(self.charger_id, 0) if station else 0
        if not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif station.geoid != vehicle.geoid:
            locations = f"{station.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to station {self.station_id} but locations do not match: {locations}"
            return SimulationStateError(message), None
        else:
            has_chargers = available_chargers > 0
            next_state = ChargingStation(self.vehicle_id,
                                         self.station_id,
                                         self.charger_id) if has_chargers else ChargeQueueing(self.vehicle_id,
                                                                                              self.station_id,
                                                                                              self.charger_id,
                                                                                              sim.sim_time)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        take a step along the route to the station
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
            updated_vehicle = moved_vehicle.modify_state(updated_state)
            return simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)
