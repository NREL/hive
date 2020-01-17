from __future__ import annotations

import copy
from typing import NamedTuple, Dict, Optional

from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.passenger import Passenger
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.vehiclestate import VehicleState
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import traverse
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import *
from hive.util.helpers import DictOps
from hive.util.units import km, seconds, SECONDS_TO_HOURS
from hive.util.exception import EntityError
from hive.model.energy.powercurve import Powercurve, powercurve_models, powercurve_energy_types
from hive.model.energy.powertrain import Powertrain, powertrain_models

from h3 import h3


class Vehicle(NamedTuple):
    """
    Tuple that represents a vehicle in the simulation.

    :param id: A unique vehicle id.
    :type id: :py:obj:`VehicleId`
    :param powertrain_id: Id for the vehicle's respective powertrain
    :type powertrain_id: :py:obj:`PowertrainId`
    :param powercurve_id: Id for the vehicle's respective powercurve
    :type powercurve_id: :py:obj:`PowercurveId`
    :param energy_source: The energy source for the vehicle
    :type energy_source: :py:obj:`EnergySource`
    :param geoid: The current location of the vehicle
    :type geoid: :py:obj:`GeoId`
    :param property_link: The current location of the vehicle on the road network
    :type property_link: :py:obj:`PropertyLink`
    :param route: The route of the vehicle. Could be empty.
    :type route: :py:obj:`Route`
    :param vehicle_state: The state that the vehicle is in.
    :type vehicle_state: :py:obj:`VehicleState`
    :param passengers: A map of passengers that are in the vehicle. Could be empty
    :type passengers: :py:obj:`Dict[PasengerId, Passengers]`
    :param station_intent: The station a vehicle is intending to charge at.
    :type station_intent: :py:obj:`Optional[StationId]`
    :param charger_intent: The charger type a vehicle intends to plug into.
    :type charger_intent: :py:obj:`Optional[Charger]`
    :param station: The station a vehicle is charging at.
    :type station: :py:obj:`Optional[Station]`
    :param plugged_in_charger: The charger type a vehicle is plugged into.
    :type plugged_in_charger: :py:obj:`Optional[Charger]`
    :param idle_time_s: A counter to track how long the vehicle has been idle.
    :type idle_time_s: :py:obj:`seconds`
    :param distance_traveled: A accumulator to track how far a vehicle has traveled.
    :type distance_traveled_km: :py:obj:`kilometers`
    """
    id: VehicleId
    powertrain_id: PowertrainId
    powercurve_id: PowercurveId
    energy_source: EnergySource
    property_link: PropertyLink

    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    passengers: Dict[PassengerId, Passenger] = {}

    station_intent: Optional[StationId] = None
    charger_intent: Optional[Charger] = None

    station: Optional[StationId] = None
    plugged_in_charger: Optional[Charger] = None

    idle_time_seconds: seconds = 0
    distance_traveled_km: km = 0.0

    @property
    def geoid(self):
        return self.property_link.link.start

    @classmethod
    def from_row(cls, row: Dict[str, str], road_network: RoadNetwork) -> Vehicle:
        """
        reads a csv row from file to generate a Vehicle

        :param row: a row of a .csv which matches hive.util.pattern.vehicle_regex.
        this string will be stripped of whitespace characters (no spaces allowed in names!)
        :param road_network: the road network, used to find the vehicle's location in the sim
        :return: a vehicle, or, an IOError if failure occurred.
        """

        if 'vehicle_id' not in row:
            raise IOError("cannot load a vehicle without a 'vehicle_id'")
        elif 'lat' not in row:
            raise IOError("cannot load a vehicle without a 'lat'")
        elif 'lon' not in row:
            raise IOError("cannot load a vehicle without a 'lon'")
        elif 'powertrain_id' not in row:
            raise IOError("cannot load a vehicle without a 'powertrain_id'")
        elif 'powercurve_id' not in row:
            raise IOError("cannot load a vehicle without a 'powercurve_id'")
        elif 'capacity' not in row:
            raise IOError("cannot load a vehicle without a 'capacity'")
        elif 'ideal_energy_limit' not in row:
            raise IOError("cannot load a vehicle without a 'ideal_energy_limit'")
        elif 'max_charge_acceptance' not in row:
            raise IOError("cannot load a vehicle without a 'max_charge_acceptance'")
        elif 'initial_soc' not in row:
            raise IOError("cannot load a vehicle without a 'initial_soc'")
        elif row['powertrain_id'] not in powertrain_models.keys():
            raise IOError(f"invalid powertrain model for vehicle: '{row['powertrain_id']}'")
        elif row['powercurve_id'] not in powercurve_models.keys():
            raise IOError(f"invalid powercurve model for vehicle: '{row['powercurve_id']}'")
        else:
            try:
                vehicle_id = row['vehicle_id']
                lat = float(row['lat'])
                lon = float(row['lon'])
                powertrain_id = row['powertrain_id']
                powercurve_id = row['powercurve_id']
                energy_type = powercurve_energy_types[powercurve_id]
                capacity = float(row['capacity'])
                iel_str = row['ideal_energy_limit']
                ideal_energy_limit = float(iel_str) if len(iel_str) > 0 else None
                max_charge_acceptance = float(row['max_charge_acceptance'])
                initial_soc = float(row['initial_soc'])

                if not 0.0 <= initial_soc <= 1.0:
                    raise IOError(f"initial soc for vehicle: '{initial_soc}' must be in range [0,1]")

                energy_source = EnergySource.build(powercurve_id,
                                                   energy_type,
                                                   capacity,
                                                   ideal_energy_limit,
                                                   max_charge_acceptance,
                                                   initial_soc)

                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                start_link = road_network.property_link_from_geoid(geoid)

                return Vehicle(
                    id=vehicle_id,
                    powertrain_id=powertrain_id,
                    powercurve_id=powercurve_id,
                    energy_source=energy_source,
                    property_link=start_link,
                )

            except ValueError:
                raise IOError(f"a numeric value could not be parsed from {row}")

    def has_passengers(self) -> bool:
        """
        Returns whether or not the vehicle has passengers.

        :return: Boolean
        """
        return len(self.passengers) > 0

    def has_route(self) -> bool:
        """
        Returns whether or not the vehicle has a route.

        :return: Boolean
        """
        return len(self.route) != 0

    def add_passengers(self, new_passengers: Tuple[Passenger, ...]) -> Vehicle:
        """
        Loads some passengers onto this vehicle

        :param new_passengers: the set of passengers we want to add
        :return: the updated vehicle
        """
        updated_passengers = copy.copy(self.passengers)
        for passenger in new_passengers:
            passenger_with_vehicle_id = passenger.add_vehicle_id(self.id)
            updated_passengers[passenger.id] = passenger_with_vehicle_id
        return self._replace(passengers=updated_passengers)

    def drop_off_passenger(self, passenger_id: PassengerId) -> Vehicle:
        """
        Drops off passengers to their destination.

        :param passenger_id:
        :return: the updated vehicle
        """
        if passenger_id not in self.passengers:
            return self
        updated_passengers = DictOps.remove_from_dict(self.passengers, passenger_id)
        return self._replace(passengers=updated_passengers)

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.energy_source})"

    def plug_in_to(self, station_id: StationId, charger: Charger) -> Vehicle:
        """
        Plugs a vehicle into a charger.

        :param station_id: id of the station to plug into
        :param charger: charger type to plug into
        :return: the updated vehicle
        """
        return self._replace(plugged_in_charger=charger, station=station_id)

    def unplug(self) -> Vehicle:
        """
        Unplugs a vehicle from a charger.

        :return: the updated vehicle
        """
        return self._replace(plugged_in_charger=None, station=None)

    def _reset_idle_stats(self) -> Vehicle:
        return self._replace(idle_time_seconds=0)

    def _reset_charge_intent(self) -> Vehicle:
        return self._replace(charger_intent=None, station_intent=None)

    def charge(self,
               powercurve: Powercurve,
               duration_seconds: seconds) -> Vehicle:

        """
        applies a charge event to a vehicle

        :param powercurve: the vehicle's powercurve model
        :param duration_seconds: duration_seconds of this time step in seconds
        :return: the updated Vehicle
        """

        if not self.plugged_in_charger:
            raise EntityError("Vehicle cannot charge without a charger.")
        if self.energy_source.is_at_ideal_energy_limit():
            # TODO: we have to return the plug to the charger. But, this is outside the scope of the vehicle..
            #  So, I think the simulation state should handle the charge end termination state.
            return self
        else:
            updated_energy_source = powercurve.refuel(self.energy_source, self.plugged_in_charger, duration_seconds)
            return self._replace(energy_source=updated_energy_source)

    def move(self, road_network: RoadNetwork, power_train: Powertrain, duration_seconds: seconds) -> Optional[Vehicle]:
        """
        Moves the vehicle and consumes energy.

        :param road_network: the road network
        :param power_train: the vehicle's powertrain model
        :param duration_seconds: the duration_seconds of this move step in seconds
        :return: the updated vehicle or None if moving is not possible.
        """
        if not self.has_route():
            return self.transition(VehicleState.IDLE)

        traverse_result = traverse(
            route_estimate=self.route,
            road_network=road_network,
            duration_seconds=duration_seconds,
        )

        if not traverse_result:
            # TODO: Need to think about edge case where vehicle gets route where origin=destination.
            no_route_veh = self.assign_route(tuple())
            return no_route_veh

        experienced_route = traverse_result.experienced_route

        energy_used = power_train.energy_cost(experienced_route)
        step_distance_km = traverse_result.traversal_distance_km

        updated_energy_source = self.energy_source.use_energy(energy_used)
        less_energy_vehicle = self.battery_swap(updated_energy_source)

        remaining_route = traverse_result.remaining_route

        new_route_vehicle = less_energy_vehicle.assign_route(remaining_route)

        if not remaining_route:
            geoid = experienced_route[-1].link.end
            updated_location_vehicle = new_route_vehicle._replace(
                property_link=road_network.property_link_from_geoid(geoid),
                distance_traveled_km=self.distance_traveled_km + step_distance_km,

            )
        else:
            updated_location_vehicle = new_route_vehicle._replace(
                property_link=remaining_route[0],
                distance_traveled_km=self.distance_traveled_km + step_distance_km,

            )

        return updated_location_vehicle

    def idle(self, time_step_seconds: seconds) -> Vehicle:
        """
        Performs an idle step.

        :param time_step_seconds: duration_seconds of the idle step in seconds
        :return: the updated vehicle
        """
        if self.vehicle_state != VehicleState.IDLE:
            raise EntityError("vehicle.idle() method called but vehicle not in IDLE state.")

        idle_energy_rate = 0.8 # (unit.kilowatthour / unit.hour)

        idle_energy_kwh = idle_energy_rate * (time_step_seconds * SECONDS_TO_HOURS)
        updated_energy_source = self.energy_source.use_energy(idle_energy_kwh)
        less_energy_vehicle = self.battery_swap(updated_energy_source)

        next_idle_time = (less_energy_vehicle.idle_time_seconds + time_step_seconds)
        vehicle_w_stats = less_energy_vehicle._replace(idle_time_seconds=next_idle_time)

        return vehicle_w_stats

    def battery_swap(self, energy_source: EnergySource) -> Vehicle:
        """
        Replaces the vehicle energy source with a new energy source.

        :param energy_source: the new energy source
        :return: the updated vehicle
        """
        return self._replace(energy_source=energy_source)

    def assign_route(self, route: Route) -> Vehicle:
        """
        Assigns a route to the vehicle

        :param route: the route to be assigned
        :return: the updated vehicle
        """
        return self._replace(route=route)

    def set_charge_intent(self, station_id: StationId, charger: Charger) -> Vehicle:
        """
        Sets the intention for a vehicle to charge.

        :param station_id: which station the vehicle intends to charge at
        :param charger: the type of charger the vehicle intends to use
        :return: the updated vehicle
        """
        return self._replace(station_intent=station_id, charger_intent=charger)

    """
    TRANSITION FUNCTIONS
    --------------------
    """

    def can_transition(self, vehicle_state: VehicleState) -> bool:
        """
        Returns whether or not a vehicle can transition to a new state from its current state

        :param vehicle_state: the new state to transition to
        :return: Boolean
        """
        if not VehicleState.is_valid(vehicle_state):
            raise TypeError("Invalid vehicle state type.")
        elif self.vehicle_state == vehicle_state:
            return False
        elif self.has_passengers():
            return False
        else:
            return True

    def transition(self, vehicle_state: VehicleState) -> Optional[Vehicle]:
        """
        Transitions the vehicle to a new state if possible.

        :param vehicle_state: the new state to transition to
        :return: the updated vehicle or None if not possible
        """
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
