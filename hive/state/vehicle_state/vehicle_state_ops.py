from typing import Tuple, Optional, NamedTuple

from hive.model.energy.charger import Charger
from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.routetraversal import traverse, RouteTraversal
from hive.runner.environment import Environment
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, RequestId
from hive.util.typealiases import VehicleId


def charge(sim: 'SimulationState',
           env: Environment,
           vehicle_id: VehicleId,
           station_id: StationId,
           charger: Charger) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState
    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle transitioning
    :param station_id: the station where we are charging
    :param charger: the charger we are using
    :return: an exception due to failure or an optional updated simulation
    """

    vehicle = sim.vehicles.get(vehicle_id)
    powercurve = env.powercurves.get(vehicle.powercurve_id) if vehicle else None
    station = sim.stations.get(station_id)

    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not powercurve:
        return SimulationStateError(f"invalid powercurve_id {vehicle.powercurve_id}"), None
    elif not station:
        return SimulationStateError(f"station {station_id} not found"), None
    elif vehicle.energy_source.is_at_ideal_energy_limit():
        return SimulationStateError(f"vehicle {vehicle_id} is full but still attempting to charge"), None
    else:
        # charge energy source
        updated_energy_source = powercurve.refuel(
            vehicle.energy_source,
            charger,
            sim.sim_timestep_duration_seconds
        )

        # determine price of charge event
        kwh_transacted = updated_energy_source.energy_kwh - vehicle.energy_source.energy_kwh  # kwh
        charger_price = station.charger_prices.get(charger)  # Currency
        charging_price = kwh_transacted * charger_price if charger_price else 0.0

        # perform updates
        updated_vehicle = vehicle.modify_energy_source(updated_energy_source).send_payment(charging_price)
        updated_station = station.receive_payment(charging_price)
        updated_sim = sim.modify_vehicle(updated_vehicle).modify_station(updated_station)

        return None, updated_sim


class MoveResult(NamedTuple):
    sim: 'SimulationState'
    route_traversal: RouteTraversal = RouteTraversal()


def _apply_route_traversal(sim: 'SimulationState',
                           env: Environment,
                           vehicle_id: VehicleId,
                           route: Route) -> Tuple[Optional[Exception], Optional[MoveResult]]:
    """
    Moves the vehicle and consumes energy.

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle moving
    :param route: the route for the vehicle
    :return: an error, or a traverse result, or (None, None) if no traversal occurred
    """
    vehicle = sim.vehicles.get(vehicle_id)
    traverse_result = traverse(
        route_estimate=route,
        duration_seconds=sim.sim_timestep_duration_seconds,
    )
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not traverse_result:
        return traverse_result, None
    elif isinstance(traverse_result, Exception):
        return traverse_result, None
    else:
        updated_vehicle = vehicle.apply_route_traversal(
            traverse_result, sim.road_network, env
        )
        updated_sim = sim.modify_vehicle(updated_vehicle)

        return None, MoveResult(updated_sim, traverse_result)


def _go_out_of_service_on_empty(sim: 'SimulationState',
                                env: Environment,
                                vehicle_id: VehicleId) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    sets a vehicle to OutOfService if it is out of energy after a move event
    :param sim: the sim after a move event
    :param env: the sim environment
    :param vehicle_id: the vehicle that moved
    :return: an optional error, or an optional sim with the out of service vehicle, or (None, None) if no changes
    """
    moved_vehicle = sim.vehicles.get(vehicle_id)
    if not moved_vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif moved_vehicle.energy_source.is_empty():
        error, exit_sim = moved_vehicle.vehicle_state.exit(sim, env)
        if error:
            return error, None
        else:
            next_state = OutOfService(vehicle_id)
            return next_state.enter(exit_sim, env)
    else:
        return None, None


def move(sim: 'SimulationState',
         env: Environment,
         vehicle_id: VehicleId,
         route: Route) -> Tuple[Optional[Exception], Optional[MoveResult]]:
    """
    moves the vehicle, and moves to OutOfService if resulting vehicle energy is empty
    :param sim: the sim state
    :param env: the sim environment
    :param vehicle_id: the vehicle to move
    :param route: the route for the vehicle
    :return: an optional error,
             or an optional sim with moved/OutOfService vehicle (or no change if no traversal occurred)
    """
    move_error, move_result = _apply_route_traversal(sim, env, vehicle_id, route)
    if move_error:
        return move_error, None
    elif not move_result:
        return None, MoveResult(sim)
    else:
        empty_check_error, empty_vehicle_sim = _go_out_of_service_on_empty(move_result.sim, env, vehicle_id)
        if empty_check_error:
            return empty_check_error, None
        elif empty_vehicle_sim:
            return None, MoveResult(empty_vehicle_sim)
        else:
            return None, move_result


def pick_up_trip(sim: 'SimulationState',
                 env: Environment,
                 vehicle_id: VehicleId,
                 request_id: RequestId) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    has a vehicle pick up a trip and receive payment for it
    :param sim: the sim state
    :param env: the sim environment
    :param vehicle_id: the vehicle picking up the request
    :param request_id: the request to pick up
    :return: an error, or, the sim with the request picked up by the vehicle
    """
    vehicle = sim.vehicles.get(vehicle_id)
    request = sim.requests.get(request_id)
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not request:
        return SimulationStateError(f"request {request_id} not found"), None
    else:
        updated_vehicle = vehicle.receive_payment(request.value)
        maybe_sim_with_vehicle = sim.modify_vehicle(updated_vehicle)
        if not maybe_sim_with_vehicle:
            return SimulationStateError(f"failed to add passengers to vehicle {vehicle_id}"), None
        else:
            update_error, updated_sim = maybe_sim_with_vehicle.remove_request(request_id)
            if update_error:
                return update_error, None
            else:
                return None, updated_sim
