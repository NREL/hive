from typing import Tuple, Optional, NamedTuple

from hive.model.roadnetwork.routetraversal import traverse, RouteTraversal

from hive.model.roadnetwork.route import Route

from hive.model.vehicle import Vehicle

from hive.util.units import Seconds

from hive.model.energy.powertrain.powertrain import Powertrain

from hive.model.roadnetwork.roadnetwork import RoadNetwork

from hive import SimulationState, Environment, VehicleId
from hive.model.energy.charger import Charger
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId


def charge(sim: SimulationState,
           env: Environment,
           vehicle_id: VehicleId,
           station_id: StationId,
           charger: Charger) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
    sim: SimulationState
    route_traversal: RouteTraversal


def move(sim: SimulationState,
         env: Environment,
         vehicle_id: VehicleId,
         route: Route) -> Tuple[Optional[Exception], Optional[MoveResult]]:
    """
    Moves the vehicle and consumes energy.

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle moving
    :param route: the route for the vehicle
    :return: the updated vehicle or None if moving is not possible.
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
