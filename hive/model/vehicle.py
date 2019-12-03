from __future__ import annotations

import copy
from typing import NamedTuple, Dict, Optional

from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.powercurve import PowerCurve
from hive.model.energy.powertrain import Powertrain
from hive.model.passenger import Passenger
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.vehiclestate import VehicleState
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import traverse
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import *


class Vehicle(NamedTuple):
    # fixed vehicle attributes
    id: VehicleId
    powertrain_id: PowertrainId
    powercurve_id: PowerCurveId
    energy_source: EnergySource
    geoid: GeoId
    property_link: PropertyLink
    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    passengers: Dict[PassengerId, Passenger] = {}
    # todo: p_locations: Dict[GeoId, PassengerId] = {}
    distance_traveled: float = 0.0

    def has_passengers(self) -> bool:
        return len(self.passengers) > 0

    def has_route(self) -> bool:
        return len(self.route) != 0

    def add_passengers(self, new_passengers: Tuple[Passenger, ...]) -> Vehicle:
        """
        loads some passengers onto this vehicle
        :param self:
        :param new_passengers: the set of passengers we want to add
        :return: the updated vehicle
        """
        updated_passengers = copy.copy(self.passengers)
        for passenger in new_passengers:
            passenger_with_vehicle_id = passenger.add_vehicle_id(self.id)
            updated_passengers[passenger.id] = passenger_with_vehicle_id
        return self._replace(passengers=updated_passengers)

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.energy_source})"

    def charge(self,
               powercurve: PowerCurve,
               charger: Charger,
               duration: Time) -> Vehicle:
        """
        applies a charge event to a vehicle
        :param powercurve: the vehicle's powercurve model
        :param charger: the charger provided by the station
        :param duration: duration of this time step
        :return: the updated Vehicle
        """
        if self.energy_source.is_full():
            return self.transition(VehicleState.IDLE)
        else:
            updated_energy_source = powercurve.refuel(self.energy_source, charger, duration)
            return self._replace(energy_source=updated_energy_source)

    def move(self, road_network: RoadNetwork, power_train: Powertrain, time_step: Time) -> Optional[Vehicle]:
        """
        Moves the vehicle and consumes energy.
        :param road_network:
        :param power_train:
        :param time_step:
        :return: the updated vehicle or None if moving is not possible.
        """
        if not self.has_route():
            return self.transition(VehicleState.IDLE)

        traverse_result = traverse(route_estimate=self.route, road_network=road_network, time_step=time_step)

        energy_used = power_train.energy_cost(traverse_result.experienced_route)

        updated_energy_source = self.energy_source.use_energy(energy_used)
        less_energy_vehicle = self.battery_swap(updated_energy_source)

        remaining_route = traverse_result.remaining_route

        new_route_vehicle = less_energy_vehicle.assign_route(remaining_route)

        updated_location_vehicle = new_route_vehicle._replace(
            geoid=remaining_route[0].link.start,
            property_link=remaining_route[0]
        )

        return updated_location_vehicle

    def battery_swap(self, battery: EnergySource) -> Vehicle:
        return self._replace(energy_source=battery)

    def assign_route(self, route: Route) -> Vehicle:
        return self._replace(route=route)

    """
    TRANSITION FUNCTIONS
    --------------------
    """

    def can_transition(self, vehicle_state: VehicleState) -> bool:
        if not VehicleState.is_valid(vehicle_state):
            raise TypeError("Invalid vehicle state type.")
        elif self.vehicle_state == vehicle_state:
            return True
        elif self.has_passengers():
            return False
        else:
            return True

    def transition(self, vehicle_state: VehicleState) -> Optional[Vehicle]:
        if self.vehicle_state == vehicle_state:
            return self
        elif self.can_transition(vehicle_state):
            return self._replace(vehicle_state=vehicle_state)
        else:
            return None
