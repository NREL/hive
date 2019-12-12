from __future__ import annotations

import copy
import re
from typing import NamedTuple, Dict, Optional

from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.passenger import Passenger
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.vehiclestate import VehicleState, VehicleStateCategory
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import traverse
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import *
from hive.util.helpers import DictOps
from hive.util.pattern import vehicle_regex
from hive.util.exception import EntityError
from hive.model.energy.powercurve import Powercurve
from hive.model.energy.powertrain import Powertrain

from h3 import h3


class Vehicle(NamedTuple):
    # fixed vehicle attributes
    id: VehicleId
    powertrain_id: PowertrainId
    powercurve_id: PowercurveId
    energy_source: EnergySource
    geoid: GeoId
    property_link: PropertyLink
    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    idle_time_s: Time = 0
    # frozenmap implementation does not yet exist
    # https://www.python.org/dev/peps/pep-0603/

    passengers: Dict[PassengerId, Passenger] = {}
    plugged_in_charger: Optional[Charger] = None
    station: Optional[StationId] = None
    charger_intent: Optional[Charger] = None
    station_intent: Optional[StationId] = None
    request: Optional[RequestId] = None
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
        elif result.group(5) not in powercurve_models.keys():
            return IOError(f"invalid energycurve model for vehicle: '{result.group(5)}'")
        else:
            try:
                vehicle_id = result.group(1)
                lat = float(result.group(2))
                lon = float(result.group(3))
                powertrain_id = result.group(4)
                energycurve_id = result.group(5)  # todo: add after issue #102 completed
                capacity = float(result.group(6))
                initial_soc = float(result.group(7))
                if not 0.0 <= initial_soc <= 1.0:
                    return IOError(f"initial soc for vehicle: '{initial_soc}' must be in range [0,1]")

                energy_type = powercurve_energy_types.get(result.group(5)) #todo: where is powercurve_energy_types?
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

    def drop_off_passenger(self, passenger_id: PassengerId) -> Vehicle:
        if passenger_id not in self.passengers:
            return self
        updated_passengers = DictOps.remove_from_entity_dict(self.passengers, passenger_id)
        return self._replace(passengers=updated_passengers)

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.energy_source})"

    def plug_in_to(self, station_id: StationId, charger: Charger):
        return self._replace(plugged_in_charger=charger, station=station_id)

    def unplug(self):
        return self._replace(plugged_in_charger=None, station=None)

    def _reset_idle_stats(self) -> Vehicle:
        return self._replace(idle_time_s=0)

    def _reset_charge_intent(self) -> Vehicle:
        return self._replace(charger_intent=None, station_intent=None)

    def charge(self,
               powercurve: Powercurve,
               duration: Time) -> Vehicle:
        """
        applies a charge event to a vehicle
        :param powercurve: the vehicle's powercurve model
        :param charger: the charger provided by the station
        :param duration: duration of this time step
        :return: the updated Vehicle
        """
        if not self.plugged_in_charger:
            raise EntityError("Vehicle cannot charge without a charger.")
        if self.energy_source.is_at_max_charge_acceptance():
            # TODO: we have to return the plug to the charger. But, this is outside the scope of the vehicle..
            #  So, I think the simulation state should handle the charge end termination state.
            return self
        else:
            updated_energy_source = powercurve.refuel(self.energy_source, self.plugged_in_charger, duration)
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

        # TODO: update self.distance_traveled based on the traversal result distance.
        experienced_route = traverse_result.experienced_route
        energy_used = power_train.energy_cost(experienced_route)

        updated_energy_source = self.energy_source.use_energy(energy_used)
        less_energy_vehicle = self.battery_swap(updated_energy_source)

        remaining_route = traverse_result.remaining_route

        new_route_vehicle = less_energy_vehicle.assign_route(remaining_route)

        if not remaining_route:
            geoid = experienced_route[-1].link.end
            updated_location_vehicle = new_route_vehicle._replace(
                geoid=geoid,
                property_link=road_network.property_link_from_geoid(geoid)
            )
        else:
            updated_location_vehicle = new_route_vehicle._replace(
                geoid=experienced_route[-1].link.end,
                property_link=remaining_route[0]
            )

        return updated_location_vehicle

    def idle(self, time_step_s: Time) -> Vehicle:
        if self.vehicle_state != VehicleState.IDLE:
            raise EntityError("vehicle.idle() method called but vehicle not in IDLE state.")

        idle_energy_kwh = 0.8 * time_step_s / 3600
        updated_energy_source = self.energy_source.use_energy(idle_energy_kwh)
        less_energy_vehicle = self.battery_swap(updated_energy_source)

        vehicle_w_stats = less_energy_vehicle._replace(idle_time_s=less_energy_vehicle.idle_time_s + time_step_s)

        return vehicle_w_stats

    def battery_swap(self, energy_source: EnergySource) -> Vehicle:
        return self._replace(energy_source=energy_source)

    def assign_route(self, route: Route) -> Vehicle:
        return self._replace(route=route)

    def set_charge_intent(self, station_id: StationId, charger: Charger):
        return self._replace(station_intent=station_id, charger_intent=charger)

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
        previous_vehicle_state = self.vehicle_state
        if previous_vehicle_state == vehicle_state:
            return self
        elif self.can_transition(vehicle_state):
            transitioned_vehicle = self._replace(vehicle_state=vehicle_state)

            if previous_vehicle_state == VehicleState.IDLE:
                return transitioned_vehicle._reset_idle_stats()
            elif previous_vehicle_state == VehicleState.DISPATCH_STATION:
                return transitioned_vehicle._reset_charge_intent()

            return transitioned_vehicle
        else:
            return None
