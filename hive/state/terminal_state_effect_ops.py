# from __future__ import annotations
#
# from typing import NamedTuple, TYPE_CHECKING, Optional
#
# from hive.state.vehicle_state import VehicleState
# from hive.util.exception import *
# from hive.util.helpers import SwitchCase
# from hive.util.typealiases import VehicleId, StationId, BaseId
#
# if TYPE_CHECKING:
#     from hive.state.simulation_state.simulation_state import SimulationState
#
#
# class TerminalStateEffectArgs(NamedTuple):
#     simulation_state: SimulationState
#     vehicle_id: VehicleId
#
#
# class TerminalStateEffectOps(SwitchCase):
#     """
#     A pattern matching class for catching terminal state conditions.
#
#     :param Key: The vehicle state to match.
#     :param Arguments: Any arguments that are needed to check the terminal state condition
#     :param Result: An updated simulation state based on the checking.
#     """
#     Key: VehicleState
#     Arguments: TerminalStateEffectArgs
#     Result: SimulationState
#
#     def _case_serving_trip(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#         if not vehicle.has_route():
#             for passenger in vehicle.passengers.values():
#                 if passenger.destination == vehicle.geoid:
#                     vehicle = vehicle.drop_off_passenger(passenger.id)
#             if vehicle.has_passengers():
#                 raise SimulationStateError('Vehicle ended trip with passengers')
#
#             vehicle = vehicle.transition(VehicleState.IDLE)
#             sim_state = sim_state.modify_vehicle(vehicle)
#
#         return sim_state
#
#     def _case_dispatch_trip(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#         at_location = sim_state.at_geoid(vehicle.geoid)
#
#         if at_location['requests'] and not vehicle.has_route():
#             for request_id in at_location['requests']:
#                 request = sim_state.requests[request_id]
#                 if request.dispatched_vehicle == vehicle.id and vehicle.can_transition(VehicleState.SERVICING_TRIP):
#                     transitioned_vehicle = vehicle.transition(VehicleState.SERVICING_TRIP)
#
#                     start = transitioned_vehicle.geoid
#                     end = request.destination
#                     route = sim_state.road_network.route(start, end)
#                     routed_vehicle = transitioned_vehicle.assign_route(route)
#
#                     sim_state = sim_state.modify_vehicle(routed_vehicle).board_vehicle(request.id, routed_vehicle.id)
#
#         return sim_state
#
#     def _case_dispatch_station(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#         station_at_location = sim_state.at_geoid(vehicle.geoid).get("station")
#         station_id_at_location: Optional[StationId] = station_at_location
#
#         if station_id_at_location and vehicle.charger_intent and not vehicle.has_route():
#             station = sim_state.stations[station_id_at_location]
#             charger = vehicle.charger_intent
#
#             if station.has_available_charger(charger):
#                 updated_station = station.checkout_charger(charger)
#                 updated_vehicle = vehicle.transition(VehicleState.CHARGING)
#                 return sim_state.modify_vehicle(updated_vehicle).modify_station(updated_station)
#             else:
#                 # FUTURE: Add station queuing?
#                 updated_vehicle = vehicle.transition(VehicleState.IDLE)
#                 return sim_state.modify_vehicle(updated_vehicle)
#         else:
#             return sim_state
#
#     def _case_dispatch_base(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#         at_location = sim_state.at_geoid(vehicle.geoid)
#
#         # TODO: Implement base stall checkout.
#         if at_location['base'] and vehicle.can_transition(VehicleState.RESERVE_BASE) and not vehicle.has_route():
#             vehicle = vehicle.transition(VehicleState.RESERVE_BASE)
#             sim_state = sim_state.modify_vehicle(vehicle)
#
#         return sim_state
#
#     def _case_repositioning(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#
#         if not vehicle.has_route():
#             vehicle = vehicle.transition(VehicleState.IDLE)
#             sim_state = sim_state.modify_vehicle(vehicle)
#
#         return sim_state
#
#     def _case_charging(self, arguments: TerminalStateEffectArgs) -> SimulationState:
#         sim_state = arguments.simulation_state
#         vehicle_id = arguments.vehicle_id
#         vehicle = sim_state.vehicles[vehicle_id]
#         at_location = sim_state.at_geoid(vehicle.geoid)
#         station_at_location = at_location.get("station")
#         station_id: Optional[StationId] = station_at_location
#
#         if station_id and vehicle.energy_source.is_at_ideal_energy_limit():
#
#             # return the charger
#             station = sim_state.stations[station_id]
#             updated_station = station.return_charger(vehicle.charger_intent)
#
#             # are we at a base?
#             base_at_location = at_location.get("base")
#             base_id: Optional[BaseId] = base_at_location
#             if base_id:
#                 base = sim_state.bases[base_id]
#                 updated_base = base.checkout_stall()
#                 updated_vehicle = vehicle.transition(VehicleState.RESERVE_BASE)
#                 return sim_state.modify_vehicle(updated_vehicle).modify_station(updated_station).modify_base(updated_base)
#             else:
#                 updated_vehicle = vehicle.transition(VehicleState.IDLE)
#                 return sim_state.modify_vehicle(updated_vehicle).modify_station(updated_station)
#         else:
#             # not a terminal state
#             return sim_state
#
#     def _default(self, arguments: Arguments) -> SimulationState:
#         return arguments.simulation_state
#
#     # todo: does having this as a field in the class mean it's constructed each time
#     #  we call TerminalStateEffectOps.switch()? perhaps it should live outside of
#     #  the class, in the file's scope, so it's only built once when the file is loaded.
#     case_statement: Dict = {
#         VehicleState.DISPATCH_TRIP: _case_dispatch_trip,
#         VehicleState.SERVICING_TRIP: _case_serving_trip,
#         VehicleState.DISPATCH_STATION: _case_dispatch_station,
#         VehicleState.DISPATCH_BASE: _case_dispatch_base,
#         VehicleState.REPOSITIONING: _case_repositioning,
#         VehicleState.CHARGING: _case_charging,
#     }
