from __future__ import annotations

from typing import Dict, Optional, NamedTuple

from hive.dispatcher.instruction import Instruction
from hive.model.vehiclestate import VehicleState
from hive.util.helpers import SwitchCase

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state import SimulationState


class VehicleTransitionEffectArgs(NamedTuple):
    simulation_state: SimulationState
    instruction: Instruction


class VehicleTransitionEffectOps(SwitchCase):
    """
    A pattern matching class for applying instant effects to a vehicle upon a transition.

    :param Key: The vehicle state to match.
    :param Arguments: Any arguments that are needed to apply the effects.
    :param Result: An updated simulation state based on the checking.
    """
    Key = VehicleState
    Arguments = VehicleTransitionEffectArgs
    Result = Optional['SimulationState']

    def _case_serving_trip(self, arguments: VehicleTransitionEffectArgs) -> Optional[SimulationState]:

        sim_state = arguments.simulation_state
        request_id = arguments.instruction.request_id
        request = sim_state.requests[request_id]
        vehicle = arguments.simulation_state.vehicles[arguments.instruction.vehicle_id]

        if not vehicle:
            return None
        elif not request or not sim_state.vehicle_at_request(vehicle.id, request.id):
            return None
        else:
            start = vehicle.property_link
            end = sim_state.road_network.property_link_from_geoid(request.destination)
            route = sim_state.road_network.route(start, end)

            vehicle_w_route = vehicle.assign_route(route)
            sim_boarded = sim_state.board_vehicle(request.id, vehicle_w_route.id)

            updated_sim_state = sim_boarded.modify_vehicle(vehicle_w_route)

            return updated_sim_state

    def _case_dispatch_trip(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:

        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        request_id = payload.instruction.request_id
        request = sim_state.requests[request_id]

        if not vehicle:
            return None
        elif not request:
            return None
        else:
            assigned_request = request.assign_dispatched_vehicle(vehicle.id, sim_state.current_time_seconds)

            start = vehicle.property_link
            end = sim_state.road_network.property_link_from_geoid(request.origin)
            route = sim_state.road_network.route(start, end)

            vehicle_w_route = vehicle.assign_route(route)

            updated_sim_state = sim_state.modify_request(assigned_request).modify_vehicle(vehicle_w_route)
            return updated_sim_state

    def _case_dispatch_station(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:

        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        station_id = payload.instruction.station_id
        charger = payload.instruction.charger

        if not vehicle:
            return None
        elif not station_id or not charger:
            return None
        elif station_id not in sim_state.stations:
            return None
        else:
            station = sim_state.stations[station_id]

            start = vehicle.property_link
            end = sim_state.road_network.property_link_from_geoid(station.geoid)
            route = sim_state.road_network.route(start, end)

            vehicle_w_route = vehicle.assign_route(route).set_charge_intent(station_id, charger)

            updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

            return updated_sim_state

    def _case_dispatch_base(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:
        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        destination = payload.instruction.location

        # todo: confirm destination is a base?
        if not vehicle:
            return None
        if not destination:
            return None
        else:
            start = vehicle.property_link
            end = sim_state.road_network.property_link_from_geoid(destination)
            route = sim_state.road_network.route(start, end)

            vehicle_w_route = vehicle.assign_route(route)

            updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

            return updated_sim_state

    def _case_repositioning(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:
        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        destination = payload.instruction.location

        if not vehicle:
            return None
        elif not destination:
            return None
        else:
            start = vehicle.property_link
            end = sim_state.road_network.property_link_from_geoid(destination)
            route = sim_state.road_network.route(start, end)

            vehicle_w_route = vehicle.assign_route(route)

            updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

            return updated_sim_state

    def _case_reserve_base(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:
        sim_state = payload.simulation_state
        if payload.instruction.vehicle_id not in payload.simulation_state.vehicles:
            return None
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        at_location = sim_state.at_geoid(vehicle.geoid)

        if not at_location['bases']:
            return None

        return sim_state

    def _case_charging_station(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:
        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        station_id = payload.instruction.station_id
        charger = payload.instruction.charger
        at_location = sim_state.at_geoid(vehicle.geoid)

        if not vehicle:
            return None
        elif not station_id or not charger:
            return None
        elif isinstance(at_location, Exception) or not at_location['stations']:
            return None
        elif station_id not in sim_state.s_locations[vehicle.geoid]:
            return None
        
        if payload.instruction.vehicle_id not in payload.simulation_state.vehicles:
            return None
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]

        station = sim_state.stations[station_id]
        if not station.has_available_charger(charger):
            return None

        station_less_charger = station.checkout_charger(charger)
        vehicle_w_charger = vehicle.plug_in_to(station_id, charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(vehicle_w_charger)

        return updated_sim_state

    def _case_charging_base(self, payload: VehicleTransitionEffectArgs) -> Optional[SimulationState]:
        sim_state = payload.simulation_state
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]
        station_id = payload.instruction.station_id
        charger = payload.instruction.charger
        at_location = sim_state.at_geoid(vehicle.geoid)

        if not vehicle:
            return None
        elif not station_id or not charger:
            return None
        elif isinstance(at_location, Exception) or not at_location['bases']:
            return None
        elif station_id not in sim_state.s_locations[vehicle.geoid]:
            return None

        if payload.instruction.vehicle_id not in payload.simulation_state.vehicles:
            return None
        vehicle = payload.simulation_state.vehicles[payload.instruction.vehicle_id]

        station = sim_state.stations[station_id]
        if not station.has_available_charger(charger):
            return None

        station_less_charger = station.checkout_charger(charger)
        vehicle_w_charger = vehicle.plug_in_to(station_id, charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(vehicle_w_charger)

        return updated_sim_state

    def _default(self, arguments: Arguments) -> Result:
        return arguments.simulation_state

    case_statement: Dict = {
        VehicleState.DISPATCH_TRIP: _case_dispatch_trip,
        VehicleState.SERVICING_TRIP: _case_serving_trip,
        VehicleState.DISPATCH_STATION: _case_dispatch_station,
        VehicleState.DISPATCH_BASE: _case_dispatch_base,
        VehicleState.REPOSITIONING: _case_repositioning,
        VehicleState.RESERVE_BASE: _case_reserve_base,
        VehicleState.CHARGING_STATION: _case_charging_station,
        VehicleState.CHARGING_BASE: _case_charging_base,
    }
