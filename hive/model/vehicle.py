from __future__ import annotations

import copy
import re
from typing import NamedTuple, Dict, Optional

from h3 import h3

from hive.model.energy.energysource import EnergySource
from hive.model.passenger import Passenger
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.vehiclestate import VehicleState
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import traverse
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import *
from hive.util.pattern import vehicle_regex
from hive.model.energy.energycurve import *
from hive.model.energy.powertrain import *


class Vehicle(NamedTuple):
    # fixed vehicle attributes
    id: VehicleId
    powertrain_id: PowertrainId
    energy_source: EnergySource
    geoid: GeoId
    property_link: PropertyLink
    soc_upper_limit: Percentage = 1.0
    soc_lower_limit: Percentage = 0.0
    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    # frozenmap implementation does not yet exist
    # https://www.python.org/dev/peps/pep-0603/
    passengers: Dict[PassengerId, Passenger] = {}
    # todo: p_locations: Dict[GeoId, PassengerId] = {}
    distance_traveled: float = 0.0

    @classmethod
    def from_string(cls, string: str, road_network: RoadNetwork) -> Union[IOError, Vehicle]:
        """
        reads a csv row from file to generate a Vehicle

        :param string: a row of a .csv which matches hive.util.pattern.vehicle_regex.
        this string will be stripped of whitespace characters (no spaces allowed in names!)
        :param road_network: the road network, used to find the vehicle's location in the sim
        :return: a vehicle, or, an IOError if failure occurred.
        """
        cleaned_string = string.replace(' ', '').replace('\t', '')
        result = re.search(vehicle_regex, cleaned_string)
        if result is None:
            return IOError(f"row did not match expected vehicle format: '{cleaned_string}'")
        elif result.group(4) not in powertrain_models.keys():
            return IOError(f"invalid powertrain model for vehicle: '{result.group(4)}'")
        elif result.group(5) not in energycurve_models.keys():
            return IOError(f"invalid energycurve model for vehicle: '{result.group(5)}'")
        else:
            try:
                vehicle_id = result.group(1)
                lat = float(result.group(2))
                lon = float(result.group(3))
                powertrain_id = result.group(4)
                energycurve_id = result.group(5) # todo: add after issue #102 completed
                capacity = float(result.group(6))
                initial_soc = float(result.group(7))
                if not 0.0 <= initial_soc <= 1.0:
                    return IOError(f"initial soc for vehicle: '{initial_soc}' must be in range [0,1]")

                energy_type = energycurve_energy_types.get(result.group(5))
                energy_source = EnergySource.build(energy_type, capacity, initial_soc)
                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                start_link = road_network.property_link_from_geoid(geoid)

                return Vehicle(
                    id=vehicle_id,
                    powertrain_id=powertrain_id,
                    energy_source=energy_source,
                    geoid=geoid,
                    property_link=start_link,
                )
            except ValueError:
                return IOError(f"a numeric value could not be parsed from {cleaned_string}")

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
