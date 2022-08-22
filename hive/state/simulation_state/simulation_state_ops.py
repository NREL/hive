from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING

import h3
from returns.result import Success, Failure, ResultE

from hive.model.sim_time import SimTime
from hive.util import DictOps
from hive.util.exception import SimulationStateError
from hive.util.fp import apply_op_to_accumulator, throw_or_return
from hive.util.typealiases import *

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.base import Base
    from hive.model.request import Request
    from hive.model.station.station import Station
    from hive.model.vehicle.vehicle import Vehicle

"""
a collection of operations to modify the SimulationState which are not
intended to be exposed to HIVE users
"""


def tick(sim: SimulationState) -> SimulationState:
    """
    advances the simulation clock


    :param sim: the simulation state
    :return: the simulation after being updated
    """

    return sim._replace(sim_time=sim.sim_time + sim.sim_timestep_duration_seconds)


def add_entity(sim: SimulationState, entity: Entity) -> SimulationState:
    """
    helper for adding an entity to the simulation

    :param sim: the simulation state
    :param entity: the entity to add

    :return: the updated simulation state
    :raises: an error if the entity cannot be added
    """
    return throw_or_return(add_entity_safe(sim, entity))


def modify_entity(sim: SimulationState, entity: Entity) -> SimulationState:
    """
    helper for modifying an entity in the simulation

    :param sim: the simulation state
    :param entity: the entity to modify

    :return: the updated simulation state
    :raises: an error if the entity cannot be modified
    """
    return throw_or_return(modify_entity_safe(sim, entity))


def add_entities(sim: SimulationState, entities: Iterable[Entity]) -> SimulationState:
    """
    helper for adding multiple entities to the simulation

    :param sim: the simulation state
    :param entities: the entities to add

    :return: the updated simulation state
    :raises: an error if any of the entities cannot be added
    """
    return throw_or_return(add_entities_safe(sim, entities))


def modify_entities(
    sim: SimulationState, entities: Iterable[Entity]
) -> SimulationState:
    """
    helper for modifying multiple entities in the simulation

    :param sim: the simulation state
    :param entities: the entities to modify

    :return: the updated simulation state
    :raises: an error if any of the entities cannot be modified
    """
    return throw_or_return(modify_entities_safe(sim, entities))


def add_entity_safe(sim: SimulationState, entity: Entity) -> ResultE[SimulationState]:
    """
    helper for adding a general entity to the simulation

    :param sim: the simulation state
    :param entity: the entity to add

    :return: the updated simulation state or an error
    """
    if entity.__class__.__name__ == "Vehicle":
        return add_vehicle_safe(sim, entity)
    if entity.__class__.__name__ == "Station":
        return add_station_safe(sim, entity)
    if entity.__class__.__name__ == "Base":
        return add_base_safe(sim, entity)
    if entity.__class__.__name__ == "Request":
        return add_request_safe(sim, entity)
    else:
        err = SimulationStateError(f"cannot add entity {entity} to simulation")
        return Failure(err)


def add_entities_safe(
    sim: SimulationState, entities: Iterable[Entity]
) -> ResultE[SimulationState]:
    """
    helper for adding multiple general entities to the simulation

    :param sim: the simulation state
    :param entities: the entities to add

    :return: the updated simulation state or an error
    """

    def _add(entity: Entity):
        def _inner(sim: SimulationState) -> ResultE[SimulationState]:
            return add_entity_safe(sim, entity)

        return _inner

    return apply_op_to_accumulator(_add, entities, sim)


def modify_entity_safe(
    sim: SimulationState, entity: Entity
) -> ResultE[SimulationState]:
    """
    helper for modifying a general entity in the simulation

    :param sim: the simulation state
    :param entity: the entity to modify

    :return: the updated simulation state or an error
    """
    if entity.__class__.__name__ == "Vehicle":
        return modify_vehicle_safe(sim, entity)
    if entity.__class__.__name__ == "Station":
        return modify_station_safe(sim, entity)
    if entity.__class__.__name__ == "Base":
        return modify_base_safe(sim, entity)
    if entity.__class__.__name__ == "Request":
        return modify_request_safe(sim, entity)
    else:
        err = SimulationStateError(f"cannot modify entity {entity} to simulation")
        return Failure(err)


def modify_entities_safe(
    sim: SimulationState, entities: Iterable[Entity]
) -> ResultE[SimulationState]:
    """
    helper for moidfying multiple general entities in the simulation

    :param sim: the simulation state
    :param entities: the entities to modify

    :return: the updated simulation state or an error
    """

    def _mod(entity: Entity):
        def _inner(sim: SimulationState) -> ResultE[SimulationState]:
            return modify_entity_safe(sim, entity)

        return _inner

    return apply_op_to_accumulator(_mod, entities, sim)


def add_request_safe(
    sim: SimulationState, request: Request
) -> ResultE[SimulationState]:
    """
    adds a request to the SimulationState

    :param sim: the simulation state
    :param request: the request to add

    :return: the updated simulation state, or an error
    """

    if not sim.road_network.geoid_within_geofence(request.origin):
        return Failure(
            SimulationStateError(
                f"origin {request.origin} not within road network geofence"
            )
        )
    else:
        search_geoid = h3.h3_to_parent(request.geoid, sim.sim_h3_search_resolution)

        updated_sim = sim._replace(
            requests=DictOps.add_to_dict(sim.requests, request.id, request),
            r_locations=DictOps.add_to_collection_dict(
                sim.r_locations, request.geoid, request.id
            ),
            r_search=DictOps.add_to_collection_dict(
                sim.r_search, search_geoid, request.id
            ),
        )
        return Success(updated_sim)


def remove_request_safe(
    sim: SimulationState, request_id: RequestId
) -> ResultE[SimulationState]:
    """
    removes a request from this simulation.
    called once a Request has been fully serviced and is no longer
    alive in the simulation.


    :param sim: the simulation state
    :param request_id: id of the request to delete
    :return: the updated simulation state (does not report failure)
    """
    request = sim.requests.get(request_id)
    if not request:
        error = SimulationStateError(
            f"attempting to remove request {request_id} which is not in simulation"
        )
        return Failure(error)
    else:
        request = sim.requests[request_id]
        search_geoid = h3.h3_to_parent(request.geoid, sim.sim_h3_search_resolution)
        updated_requests = DictOps.remove_from_dict(sim.requests, request.id)
        updated_r_locations = DictOps.remove_from_collection_dict(
            sim.r_locations, request.geoid, request.id
        )
        updated_r_search = DictOps.remove_from_collection_dict(
            sim.r_search, search_geoid, request.id
        )

        updated_sim = sim._replace(
            requests=updated_requests,
            r_locations=updated_r_locations,
            r_search=updated_r_search,
        )

        return Success(updated_sim)


def remove_request(
    sim: SimulationState, request_id: RequestId
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = remove_request_safe(sim, request_id)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def modify_request_safe(
    sim: SimulationState, updated_request: Request
) -> ResultE[SimulationState]:
    """
    given an updated request, update the SimulationState with that request

    :param sim: the simulation state
    :param updated_request:
    :return: the updated simulation, or an error
    """
    request = sim.requests.get(updated_request.id)
    if not request:
        error = SimulationStateError(
            f"cannot update request {updated_request.id}, it was not already in the sim"
        )
        return Failure(error)
    elif not sim.road_network.geoid_within_geofence(updated_request.origin):
        error = SimulationStateError(
            f"cannot modify request {updated_request.id}: origin not within road network"
        )
        return Failure(error)
    elif not sim.road_network.geoid_within_geofence(updated_request.destination):
        error = SimulationStateError(
            f"cannot modify request {updated_request.id}: destination not within road network"
        )
        return Failure(error)
    else:
        result = DictOps.update_entity_dictionaries(
            updated_request,
            sim.requests,
            sim.r_locations,
            sim.r_search,
            sim.sim_h3_search_resolution,
        )

        updated_sim = sim._replace(
            requests=result.entities if result.entities else sim.requests,
            r_locations=result.locations if result.locations else sim.r_locations,
            r_search=result.search if result.search else sim.r_search,
        )
        return Success(updated_sim)


def modify_request(
    sim: SimulationState, updated_request: Request
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = modify_request_safe(sim, updated_request)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def add_vehicle_safe(
    sim: SimulationState, vehicle: Vehicle
) -> ResultE[SimulationState]:
    """
    adds a vehicle into the region supported by the RoadNetwork in this SimulationState


    :param sim: the simulation state
    :param vehicle: a vehicle
    :return: updated SimulationState, or SimulationStateError
    """
    if not sim.road_network.geoid_within_geofence(vehicle.geoid):
        error = SimulationStateError(
            f"cannot add vehicle {vehicle.id} to sim: not within road network geofence"
        )
        return Failure(error)
    else:
        search_geoid = h3.h3_to_parent(vehicle.geoid, sim.sim_h3_search_resolution)
        updated_v_locations = DictOps.add_to_collection_dict(
            sim.v_locations, vehicle.geoid, vehicle.id
        )
        updated_v_search = DictOps.add_to_collection_dict(
            sim.v_search, search_geoid, vehicle.id
        )
        updated_sim = sim._replace(
            vehicles=DictOps.add_to_dict(sim.vehicles, vehicle.id, vehicle),
            v_locations=updated_v_locations,
            v_search=updated_v_search,
        )
        return Success(updated_sim)


def modify_vehicle_safe(
    sim: SimulationState, updated_vehicle: Vehicle
) -> ResultE[SimulationState]:
    """
    given an updated vehicle, update the SimulationState with that vehicle

    :param sim: the simulation state
    :param updated_vehicle: the vehicle after calling a transition function and .step()
    :return: the updated simulation, or an error
    """

    # TODO: since the geofence is is made up of hexes, it is possible to exit the geofence mid route when
    #   traveling between two protruding hexes. I think we can allow this since we guarantee that a request
    #   o-d pair will always be within the geofence.
    vehicle = sim.vehicles.get(updated_vehicle.id)
    if not vehicle:
        error = SimulationStateError(
            f"cannot update vehicle {vehicle.id}, it was not already in the sim"
        )
        return Failure(error)
    elif not sim.road_network.geoid_within_geofence(updated_vehicle.geoid):
        error = SimulationStateError(
            f"cannot add vehicle {updated_vehicle.id} to sim: not within road network"
        )
        return Failure(error)
    else:
        updated_dictionaries = DictOps.update_entity_dictionaries(
            updated_vehicle,
            sim.vehicles,
            sim.v_locations,
            sim.v_search,
            sim.sim_h3_search_resolution,
        )

        updated_sim = sim._replace(
            vehicles=updated_dictionaries.entities
            if updated_dictionaries.entities
            else sim.vehicles,
            v_locations=updated_dictionaries.locations
            if updated_dictionaries.locations
            else sim.v_locations,
            v_search=updated_dictionaries.search
            if updated_dictionaries.search
            else sim.v_search,
        )
        return Success(updated_sim)


def modify_vehicle(
    sim: SimulationState, updated_vehicle: Vehicle
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = modify_vehicle_safe(sim, updated_vehicle)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def remove_vehicle_safe(
    sim: SimulationState, vehicle_id: VehicleId
) -> ResultE[SimulationState]:
    """
    removes the vehicle from play (perhaps to simulate a broken vehicle or end of a shift)


    :param sim: the simulation state
    :param vehicle_id: the id of the vehicle
    :return: the updated simulation state
    """
    if not isinstance(vehicle_id, VehicleId):
        error = SimulationStateError(
            f"remove_vehicle() takes a VehicleId (str), not a {type(vehicle_id)}"
        )
        return Failure(error)
    elif vehicle_id not in sim.vehicles:
        error = SimulationStateError(
            f"attempting to remove vehicle {vehicle_id} which is not in simulation"
        )
        return Failure(error)
    else:
        vehicle = sim.vehicles[vehicle_id]
        search_geoid = h3.h3_to_parent(vehicle.geoid, sim.sim_h3_search_resolution)

        updated_sim = sim._replace(
            vehicles=DictOps.remove_from_dict(sim.vehicles, vehicle_id),
            v_locations=DictOps.remove_from_collection_dict(
                sim.v_locations, vehicle.geoid, vehicle_id
            ),
            v_search=DictOps.remove_from_collection_dict(
                sim.v_search, search_geoid, vehicle_id
            ),
        )
        return Success(updated_sim)


def remove_vehicle(
    sim: SimulationState, vehicle_id: VehicleId
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = remove_vehicle_safe(sim, vehicle_id)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def pop_vehicle_safe(
    sim: SimulationState, vehicle_id: VehicleId
) -> ResultE[Tuple[SimulationState, Vehicle]]:
    """
    removes a vehicle from this SimulationState, which updates the state and also returns the vehicle.
    supports shipping this vehicle to another cluster node.


    :param sim: the simulation state
    :param vehicle_id: the id of the vehicle to pop
    :return: either a Tuple containing the updated state and the vehicle, or, an error
    """
    vehicle = sim.vehicles.get(vehicle_id)
    if not vehicle:
        error = SimulationStateError(
            f"attempting to pop vehicle {vehicle_id} which is not in simulation"
        )
        return Failure(error)
    else:
        remove_result = remove_vehicle_safe(sim, vehicle_id)
        if isinstance(remove_result, Failure):
            response = SimulationStateError(
                f"failure in pop_vehicle for vehicle {vehicle_id}"
            )
            response.__cause__ = remove_result.failure()
            return Failure(error)
        else:
            return Success((remove_result.unwrap(), vehicle))


def pop_vehicle(
    sim: SimulationState, vehicle_id: VehicleId
) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, Vehicle]]]:
    # TODO: refactor usage of this function to be the safe version
    result = pop_vehicle_safe(sim, vehicle_id)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def add_station_safe(
    sim: SimulationState, station: Station
) -> ResultE[SimulationState]:
    """
    adds a station to the simulation


    :param sim: the simulation state
    :param station: the station to add
    :return: the updated SimulationState, or a error = SimulationStateError
    """
    if not sim.road_network.geoid_within_geofence(station.geoid):
        error = SimulationStateError(
            f"cannot add station {station.id} to sim: not within road network geofence"
        )
        return Failure(error)
    else:
        search_geoid = h3.h3_to_parent(station.geoid, sim.sim_h3_search_resolution)
        updated_s_locations = DictOps.add_to_collection_dict(
            sim.s_locations, station.geoid, station.id
        )
        updated_s_search = DictOps.add_to_collection_dict(
            sim.s_search, search_geoid, station.id
        )
        updated_sim = sim._replace(
            stations=DictOps.add_to_dict(sim.stations, station.id, station),
            s_locations=updated_s_locations,
            s_search=updated_s_search,
        )
        return Success(updated_sim)


def remove_station_safe(
    sim: SimulationState, station_id: StationId
) -> ResultE[SimulationState]:
    """
    remove a station from the simulation. maybe they closed due to inclement weather.


    :param sim: the simulation state
    :param station_id: the id of the station to remove
    :return: the updated simulation state, or an exception
    """
    station = sim.stations.get(station_id)
    if not station:
        error = SimulationStateError(
            f"cannot remove station {station_id}, it does not exist"
        )
        return Failure(error)
    else:
        search_geoid = h3.h3_to_parent(station.geoid, sim.sim_h3_search_resolution)
        updated_s_locations = DictOps.remove_from_collection_dict(
            sim.s_locations, station.geoid, station_id
        )
        updated_s_search = DictOps.remove_from_collection_dict(
            sim.s_search, search_geoid, station_id
        )

        updated_sim = sim._replace(
            stations=DictOps.remove_from_dict(sim.stations, station_id),
            s_locations=updated_s_locations,
            s_search=updated_s_search,
        )
        return Success(updated_sim)


def remove_station(
    sim: SimulationState, station_id: StationId
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = remove_station_safe(sim, station_id)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def modify_station_safe(
    sim: SimulationState, updated_station: Station
) -> ResultE[SimulationState]:
    """
    given an updated station, update the SimulationState with that station


    :param sim: the simulation state
    :param updated_station: the revised station data
    :return: the updated simulation, or an error
    """
    station = sim.stations.get(updated_station.id)
    if not station:
        error = SimulationStateError(
            f"cannot update station {updated_station.id}, it was not already in the sim"
        )
        return Failure(error)
    elif station.geoid != updated_station.geoid:
        msg = f"station {station.id} attempting to move from {station.geoid} to {updated_station.geoid}, which is not permitted"
        error = SimulationStateError(msg)
        return Failure(error)
    elif not sim.road_network.geoid_within_geofence(updated_station.geoid):
        error = SimulationStateError(
            f"cannot add station {station.id} to sim: not within road network geofence"
        )
        return Failure(error)
    else:
        updated_sim = sim._replace(
            stations=DictOps.add_to_dict(
                sim.stations, updated_station.id, updated_station
            )
        )
        return Success(updated_sim)


def modify_station(
    sim: SimulationState, updated_station: Station
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = modify_station_safe(sim, updated_station)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def add_base_safe(sim: SimulationState, base: Base) -> ResultE[SimulationState]:
    """
    adds a base to the simulation


    :param sim: the simulation state
    :param base: the base to add
    :return: the updated SimulationState, or a SimulationStateError
    """
    if not sim.road_network.geoid_within_geofence(base.geoid):
        error = SimulationStateError(
            f"cannot add base {base.id} to sim: not within road network geofence"
        )
        return Failure(error)
    else:
        search_geoid = h3.h3_to_parent(base.geoid, sim.sim_h3_search_resolution)
        updated_b_locations = DictOps.add_to_collection_dict(
            sim.b_locations, base.geoid, base.id
        )
        updated_b_search = DictOps.add_to_collection_dict(
            sim.b_search, search_geoid, base.id
        )

        updated_sim = sim._replace(
            bases=DictOps.add_to_dict(sim.bases, base.id, base),
            b_locations=updated_b_locations,
            b_search=updated_b_search,
        )
        return Success(updated_sim)


def remove_base_safe(sim: SimulationState, base_id: BaseId) -> ResultE[SimulationState]:
    """
    remove a base from the simulation. all your base belong to us.


    :param sim: the simulation state
    :param base_id: the id of the base to remove
    :return: the updated simulation state, or an exception
    """
    base = sim.bases.get(base_id)
    if not base:
        error = SimulationStateError(f"cannot remove base {base_id}, it does not exist")
        return Failure(error)
    else:
        search_geoid = h3.h3_to_parent(base.geoid, sim.sim_h3_search_resolution)
        updated_b_locations = DictOps.remove_from_collection_dict(
            sim.b_locations, base.geoid, base_id
        )
        updated_b_search = DictOps.remove_from_collection_dict(
            sim.b_search, search_geoid, base_id
        )
        updated_sim = sim._replace(
            bases=DictOps.remove_from_dict(sim.bases, base_id),
            b_locations=updated_b_locations,
            b_search=updated_b_search,
        )
        return Success(updated_sim)


def remove_base(
    sim: SimulationState, base_id: BaseId
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = remove_base_safe(sim, base_id)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def modify_base_safe(
    sim: SimulationState, updated_base: Base
) -> ResultE[SimulationState]:
    """
    given an updated base, update the SimulationState with that base
    invariant: base locations will not be changed!


    :param sim: the simulation state
    :param updated_base:
    :return: the updated simulation, or an error
    """
    base = sim.bases.get(updated_base.id)
    if not base:
        error = SimulationStateError(
            f"cannot update base {updated_base.id}, it was not already in the sim"
        )
        return Failure(error)
    elif base.geoid != updated_base.geoid:
        msg = f"base {base.id} attempting to move from {base.geoid} to {updated_base.geoid}, which is not permitted"
        error = SimulationStateError(msg)
        return Failure(error)
    elif not sim.road_network.geoid_within_geofence(updated_base.geoid):
        error = SimulationStateError(
            f"cannot add base {updated_base.id} to sim: not within road network geofence"
        )
        return Failure(error)
    else:
        updated_sim = sim._replace(
            bases=DictOps.add_to_dict(sim.bases, updated_base.id, updated_base)
        )
        return Success(updated_sim)


def modify_base(
    sim: SimulationState, updated_base: Base
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    # TODO: refactor usage of this function to be the safe version
    result = modify_base_safe(sim, updated_base)
    if isinstance(result, Failure):
        return result.failure(), None
    else:
        return None, result.unwrap()


def update_road_network(sim: SimulationState, sim_time: SimTime) -> SimulationState:
    """
    trigger the update of the road network model based on the current sim time


    :param sim: the simulation state
    :param sim_time: the current sim time
    :return: updated simulation state (and road network)
    """
    return sim._replace(road_network=sim.road_network.update(sim_time))
