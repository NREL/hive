from __future__ import annotations
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING

from hive.model.roadnetwork.route import Route
from hive.model.roadnetwork.routetraversal import traverse, RouteTraversal
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.vehicle_event_ops import vehicle_move_event, vehicle_charge_event, report_pickup_request
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, RequestId, ChargerId
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment


def charge(sim: SimulationState,
           env: Environment,
           vehicle_id: VehicleId,
           station_id: StationId,
           charger_id: ChargerId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle transitioning
    :param station_id: the station where we are charging
    :param charger_id: the charger_id we are using
    :return: an exception due to failure or an optional updated simulation
    """

    vehicle = sim.vehicles.get(vehicle_id)
    mechatronics = env.mechatronics.get(vehicle.mechatronics_id) if vehicle else None
    charger = env.chargers.get(charger_id)
    station = sim.stations.get(station_id)

    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not mechatronics:
        return SimulationStateError(f"invalid mechatronics_id {vehicle.mechatronics_id}"), None
    elif not charger:
        return SimulationStateError(f"invalid charger_id {charger_id}"), None
    elif not station:
        return SimulationStateError(f"station {station_id} not found"), None
    elif mechatronics.is_full(vehicle):
        return SimulationStateError(f"vehicle {vehicle_id} is full but still attempting to charge"), None
    else:
        charged_vehicle, _ = mechatronics.add_energy(vehicle, charger, sim.sim_timestep_duration_seconds)

        # determine price of charge event
        kwh_transacted = charged_vehicle.energy[charger.energy_type] - vehicle.energy[charger.energy_type]  # kwh
        charger_price = station.charger_prices_per_kwh.get(charger_id)  # Currency
        charging_price = kwh_transacted * charger_price if charger_price else 0.0

        # perform updates
        updated_vehicle = charged_vehicle.send_payment(charging_price)
        updated_station = station.receive_payment(charging_price)

        veh_error, sim_with_vehicle = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        if veh_error:
            return veh_error, None
        else:
            report = vehicle_charge_event(vehicle, updated_vehicle, sim_with_vehicle, updated_station, charger)
            env.reporter.file_report(report)

            return simulation_state_ops.modify_station(sim_with_vehicle, updated_station)


class MoveResult(NamedTuple):
    sim: SimulationState
    prev_vehicle: Optional[Vehicle] = None
    next_vehicle: Optional[Vehicle] = None
    route_traversal: RouteTraversal = RouteTraversal()


def _apply_route_traversal(sim: SimulationState,
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
    mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
    error, traverse_result = traverse(
        route_estimate=route,
        duration_seconds=sim.sim_timestep_duration_seconds,
    )
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not mechatronics:
        return SimulationStateError(f"cannot find {vehicle.mechatronics_id} in environment"), None
    elif error:
        return error, None
    elif not traverse_result:
        return traverse_result, None
    elif isinstance(traverse_result, Exception):
        return traverse_result, None
    else:
        # todo: we allow the agent to traverse only bounded by time, not energy;
        #   so, it is possible for the vehicle to travel farther in a time step than
        #   they have fuel to travel. this can create an error on the location of
        #   any agents at the time step where they run out of fuel. feels like an
        #   acceptable edge case but we could improve. rjf 20200309

        experienced_route = traverse_result.experienced_route
        less_energy_vehicle = mechatronics.move(vehicle, experienced_route)
        step_distance_km = traverse_result.traversal_distance_km
        remaining_route = traverse_result.remaining_route

        if not remaining_route:
            geoid = experienced_route[-1].end
            link = sim.road_network.link_from_geoid(geoid)
            updated_vehicle = less_energy_vehicle.modify_link(link=link).tick_distance_traveled_km(step_distance_km)
        else:
            updated_vehicle = less_energy_vehicle.modify_link(link=remaining_route[0]).tick_distance_traveled_km(
                step_distance_km)

        error, updated_sim = simulation_state_ops.modify_vehicle(
            sim,
            updated_vehicle,
        )
        if error:
            return error, None
        else:
            return None, MoveResult(updated_sim, vehicle, updated_vehicle, traverse_result)


def _go_out_of_service_on_empty(sim: SimulationState,
                                env: Environment,
                                vehicle_id: VehicleId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    sets a vehicle to OutOfService if it is out of energy after a move event

    :param sim: the sim after a move event
    :param env: the sim environment
    :param vehicle_id: the vehicle that moved
    :return: an optional error, or an optional sim with the out of service vehicle, or (None, None) if no changes
    """
    moved_vehicle = sim.vehicles.get(vehicle_id)
    mechatronics = env.mechatronics.get(moved_vehicle.mechatronics_id)
    if not moved_vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not mechatronics:
        return SimulationStateError(f"cannot find {moved_vehicle.mechatronics_id} in environment"), None
    elif mechatronics.is_empty(moved_vehicle):
        error, exit_sim = moved_vehicle.vehicle_state.exit(sim, env)
        if error:
            return error, None
        elif not exit_sim:
            # the previous state does not allow exit to OutOfService
            return SimulationStateError(
                f"vehicle {moved_vehicle.id} cannot exit state {moved_vehicle.vehicle_state.__class__.__name__}"), None
        else:
            next_state = OutOfService(vehicle_id)
            return next_state.enter(exit_sim, env)
    else:
        return None, None


def move(sim: SimulationState,
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
            report = vehicle_move_event(move_result, env)
            env.reporter.file_report(report)
            return None, move_result


def pick_up_trip(sim: SimulationState,
                 env: Environment,
                 vehicle_id: VehicleId,
                 request_id: RequestId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
        mod_error, maybe_sim_with_vehicle = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        if mod_error:
            return mod_error, None
        else:
            try:
                report = report_pickup_request(updated_vehicle, request, maybe_sim_with_vehicle)
                env.reporter.file_report(report)
            except:
                # previous state may not be DispatchTrip (may not have expected attributes
                pass
            return simulation_state_ops.remove_request(maybe_sim_with_vehicle, request_id)
