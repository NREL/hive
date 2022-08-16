from __future__ import annotations

from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING

from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.route import Route, empty_route
from hive.model.roadnetwork.routetraversal import traverse, RouteTraversal
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.vehicle_event_ops import vehicle_move_event, vehicle_charge_event
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, ChargerId
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment


def charge(sim: SimulationState, env: Environment, vehicle_id: VehicleId, station_id: StationId,
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
    station = sim.stations.get(station_id)
    charger_err, charger = station.get_charger_instance(charger_id) if station is not None else None

    context = f"vehicle {vehicle_id} attempting to charge at station {station_id} with charger {charger_id}"

    if not vehicle:
        return SimulationStateError(f"vehicle not found; context: {context}"), None
    elif not mechatronics:
        return SimulationStateError(
            f"invalid mechatronics_id {vehicle.mechatronics_id}; context: {context}"), None
    elif not station:
        return SimulationStateError(f"station not found; context {context}"), None
    elif charger_err is not None:
        return charger_err, None
    elif not charger:
        return SimulationStateError(f"invalid charger_id; context: {context}"), None
    elif mechatronics.is_full(vehicle):
        return SimulationStateError(
            f"vehicle is full but still attempting to charge; context {context}"), None
    else:
        charged_vehicle, _ = mechatronics.add_energy(vehicle, charger,
                                                     sim.sim_timestep_duration_seconds)

        # determine price of charge event
        kwh_transacted = charged_vehicle.energy[charger.energy_type] - vehicle.energy[
            charger.energy_type]  # kwh
        charger_price = station.get_price(charger_id)  # Currency
        charging_price = kwh_transacted * charger_price if charger_price else 0.0

        # perform updates
        updated_vehicle = charged_vehicle.send_payment(charging_price)
        updated_station = station.receive_payment(charging_price)

        veh_error, sim_with_vehicle = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        if veh_error:
            response = SimulationStateError(f"failure during charge for vehicle {vehicle.id}")
            response.__cause__ = veh_error
            return response, None
        else:
            report = vehicle_charge_event(vehicle, updated_vehicle, sim_with_vehicle,
                                          updated_station, charger, mechatronics)
            env.reporter.file_report(report)

            return simulation_state_ops.modify_station(sim_with_vehicle, updated_station)


class MoveResult(NamedTuple):
    sim: SimulationState
    prev_vehicle: Optional[Vehicle] = None
    next_vehicle: Optional[Vehicle] = None
    route_traversal: RouteTraversal = RouteTraversal()


def _go_out_of_service_on_empty(
        sim: SimulationState, env: Environment,
        vehicle_id: VehicleId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    sets a vehicle to OutOfService if it is out of energy after a move event.
    this assumes we've already confirmed a vehicle is out of energy.

    :param sim: the sim before the move event
    :param env: the sim environment
    :param vehicle_id: the vehicle that moved and ran out of energy
    :return: an optional error, or an optional sim with the out of service vehicle
    """
    # TODO: ways we can improve this:
    # - find the exact point in the route where a vehicle runs out of energy and move it there before transitioning
    #   to out of service.
    # - report stranded passengers if we're servicing a trip when this happens.
    next_state = OutOfService.build(vehicle_id)
    return next_state.enter(sim, env)


def move(sim: SimulationState, env: Environment,
         vehicle_id: VehicleId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    Moves the vehicles.
    Transitions to OutOfService if the vehicle is empty

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle moving
    :return: an error, or a sim with the moved vehicle, or (None, None) if no changes
    """
    context = f"vehicle {vehicle_id} attempting to move"

    vehicle = sim.vehicles.get(vehicle_id)
    if not vehicle:
        return SimulationStateError(f"vehicle not found; context {context}"), None

    mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
    if not mechatronics:
        return SimulationStateError(f"cannot find {vehicle.mechatronics_id} in environment"), None

    if not hasattr(vehicle.vehicle_state, 'route'):
        return SimulationStateError(f"vehicle state does not have route; context {context}"), None
    else:
        route = vehicle.vehicle_state.route

    error, traverse_result = traverse(
        route_estimate=route,
        duration_seconds=int(sim.sim_timestep_duration_seconds),
    )
    if error:
        return error, None

    if not traverse_result.experienced_route:
        # vehicle did not traverse so we set an empty route
        updated_vehicle_state = vehicle.vehicle_state.update_route(route=empty_route())
        updated_vehicle = vehicle.modify_vehicle_state(updated_vehicle_state)
    else:
        experienced_route = traverse_result.experienced_route
        remaining_route = traverse_result.remaining_route
        less_energy_vehicle = mechatronics.consume_energy(vehicle, experienced_route)
        if mechatronics.is_empty(less_energy_vehicle):
            # impossible to move, let's transition to OutOfService
            return _go_out_of_service_on_empty(sim, env, vehicle_id)

        step_distance_km = traverse_result.traversal_distance_km
        last_link_traversed = experienced_route[-1]

        vehicle_position = EntityPosition(last_link_traversed.link_id, last_link_traversed.end)
        new_position_vehicle = less_energy_vehicle.modify_position(
            position=vehicle_position).tick_distance_traveled_km(step_distance_km)

        new_route_state = new_position_vehicle.vehicle_state.update_route(route=remaining_route)
        updated_vehicle = new_position_vehicle.modify_vehicle_state(new_route_state)

        report = vehicle_move_event(sim, vehicle, updated_vehicle, traverse_result, env)
        env.reporter.file_report(report)

    error, moved_sim = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
    if error:
        response = SimulationStateError(
            f"failure during _apply_route_traversal for vehicle {vehicle.id}")
        response.__cause__ = error
        return response, None
    else:
        return None, moved_sim

