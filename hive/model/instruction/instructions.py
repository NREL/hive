from __future__ import annotations

from typing import NamedTuple, Optional, TYPE_CHECKING

from hive.model.instruction.instruction_interface import Instruction
from hive.model.vehiclestate import VehicleState
from hive.util.typealiases import StationId, VehicleId, RequestId, GeoId
from hive.model.energy.charger import Charger

if TYPE_CHECKING:
    from hive.state.simulation_state import SimulationState

CHARGE_STATES = {VehicleState.CHARGING_STATION, VehicleState.CHARGING_BASE}


class DispatchTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.request_id not in sim_state.requests:
            return None
        request = sim_state.requests[self.request_id]

        if not vehicle.can_transition(VehicleState.DISPATCH_TRIP):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            # TODO: we should think about the implications of not having an explicit paring between the vehicle
            #  and the station. what if we had two stations at the same location?
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.DISPATCH_TRIP)

        assigned_request = request.assign_dispatched_vehicle(vehicle.id, sim_state.sim_time)

        start = vehicle.property_link
        end = sim_state.road_network.property_link_from_geoid(request.origin)
        route = sim_state.road_network.route(start, end)

        vehicle = vehicle.assign_route(route)

        updated_sim_state = sim_state.modify_request(assigned_request).modify_vehicle(vehicle)
        return updated_sim_state


class ServeTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.request_id not in sim_state.requests:
            return None
        request = sim_state.requests[self.request_id]
        if not sim_state.vehicle_at_request(vehicle.id, request.id):
            return None

        if not vehicle.can_transition(VehicleState.SERVICING_TRIP):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.SERVICING_TRIP)

        start = vehicle.property_link
        end = sim_state.road_network.property_link_from_geoid(request.destination)
        route = sim_state.road_network.route(start, end)

        vehicle = vehicle.assign_route(route)
        sim_boarded = sim_state.board_vehicle(request.id, vehicle.id)

        updated_sim_state = sim_boarded.modify_vehicle(vehicle)

        return updated_sim_state


class DispatchStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.station_id not in sim_state.stations:
            return None
        station = sim_state.stations[self.station_id]

        if not vehicle.can_transition(VehicleState.DISPATCH_STATION):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.DISPATCH_STATION)

        start = vehicle.property_link
        end = sim_state.road_network.property_link_from_geoid(station.geoid)
        route = sim_state.road_network.route(start, end)

        vehicle = vehicle.assign_route(route).set_charge_intent(self.charger)

        updated_sim_state = sim_state.modify_vehicle(vehicle)

        return updated_sim_state


class ChargeStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.station_id not in sim_state.stations:
            return None
        station = sim_state.stations[self.station_id]
        if not station.has_available_charger(self.charger):
            return None

        if not vehicle.can_transition(VehicleState.CHARGING_STATION):
            return None
        updated_vehicle = vehicle.transition(VehicleState.CHARGING_STATION).set_charge_intent(self.charger)

        at_location = sim_state.at_geoid(updated_vehicle.geoid)
        if not at_location['stations']:
            return None

        station_less_charger = station.checkout_charger(self.charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(updated_vehicle)

        return updated_sim_state


class ChargeBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.station_id not in sim_state.stations:
            return None
        station = sim_state.stations[self.station_id]
        if not station.has_available_charger(self.charger):
            return None

        if not vehicle.can_transition(VehicleState.CHARGING_BASE):
            return None
        updated_vehicle = vehicle.set_charge_intent(self.charger).transition(VehicleState.CHARGING_BASE)

        at_location = sim_state.at_geoid(updated_vehicle.geoid)
        if not at_location['bases']:
            return None

        station_less_charger = station.checkout_charger(self.charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(updated_vehicle)

        return updated_sim_state


class DispatchBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: GeoId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        if not vehicle.can_transition(VehicleState.DISPATCH_BASE):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.DISPATCH_BASE)

        start = vehicle.property_link
        end = sim_state.road_network.property_link_from_geoid(self.destination)
        route = sim_state.road_network.route(start, end)

        vehicle_w_route = vehicle.assign_route(route)

        updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

        return updated_sim_state


class RepositionInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: GeoId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        if not vehicle.can_transition(VehicleState.REPOSITIONING):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.REPOSITIONING)

        start = vehicle.property_link
        end = sim_state.road_network.property_link_from_geoid(self.destination)
        route = sim_state.road_network.route(start, end)

        vehicle_w_route = vehicle.assign_route(route)

        updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

        return updated_sim_state


class ReserveBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        at_location = sim_state.at_geoid(vehicle.geoid)
        if not at_location['bases']:
            return None

        if not vehicle.can_transition(VehicleState.RESERVE_BASE):
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            stations_at_location = sim_state.at_geoid(vehicle.geoid).get("stations")
            station_id = stations_at_location[0]
            station = sim_state.stations[station_id]
            update_station = station.return_charger(vehicle.charger_intent)
            sim_state = sim_state.modify_station(update_station)

        vehicle = vehicle.transition(VehicleState.RESERVE_BASE)
        updated_sim_state = sim_state.modify_vehicle(vehicle)

        return updated_sim_state
