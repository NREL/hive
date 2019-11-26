from __future__ import annotations

import copy
from typing import NamedTuple, Dict, Optional

from h3 import h3

from hive.model.energy.energysource import EnergySource
from hive.model.energy.powertrain import Powertrain
from hive.model.passenger import Passenger

from hive.model.charger import Charger
from hive.model.vehiclestate import VehicleState, VehicleStateCategory

from hive.model.roadnetwork.routetraversal import Route
from hive.util.exception import *
from hive.util.typealiases import *


class Vehicle(NamedTuple):
    # fixed vehicle attributes
    id: VehicleId
    powertrain_id: PowertrainId
    battery: EnergySource
    position: Position
    geoid: GeoId
    soc_upper_limit: Percentage = 1.0
    soc_lower_limit: Percentage = 0.0
    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    # frozenmap implementation does not yet exist
    # https://www.python.org/dev/peps/pep-0603/
    passengers: Dict[PassengerId, Passenger] = {}
    # todo: p_locations: Dict[GeoId, PassengerId] = {}
    distance_traveled: float = 0.0

    def has_passengers(self) -> bool:
        return len(self.passengers) > 0

    def has_route(self) -> bool:
        return not self.route.is_empty()

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
        return f"Vehicle({self.id},{self.vehicle_state},{self.battery})"

    def _move(self, powertrain: Powertrain) -> Vehicle:
        # take one route step
        # todo: need to update the GeoId here; i think this means the RoadNetwork
        #  needs to be in scope (a parameter of step/_move)
        #  a quick fix for now:
        this_route_step, updated_route = self.route.step_route()
        sim_h3_resolution = 11  # should come from simulation
        new_geoid = h3.geo_to_h3(this_route_step.position.lat, this_route_step.position.lon, sim_h3_resolution)
        this_fuel_usage = powertrain.energy_cost(this_route_step)
        updated_battery = self.battery.use_energy(this_fuel_usage)
        return self._replace(
            position=this_route_step.position,
            geoid=new_geoid,
            battery=updated_battery,
            route=updated_route,
            distance_traveled=self.distance_traveled + this_route_step.great_circle_distance
        )

    def step(self, engine: Optional[Powertrain], charger: Optional[Charger]) -> Vehicle:
        """
        when an agent stays in the same vehicle state for two subsequent time steps,
        we perform their action in the transition.

        this may be charging, or, following a route.
        also may make a default state transition to IDLE if it is legal.
        :return:
        """
        step_type = VehicleStateCategory.from_vehicle_state(self.vehicle_state)

        if step_type == VehicleStateCategory.DO_NOTHING:
            return self  # NOOP

        elif step_type == VehicleStateCategory.CHARGE:
            # perform a CHARGE step
            if charger is None:
                raise StateOfChargeError(f"{self} cannot charge without a plugged-in charger")
            elif self.battery.soc() >= self.soc_upper_limit:
                # fall into IDLE state
                return self.transition(VehicleState.IDLE)
            else:
                # take one charging step
                return self._replace(
                    battery=self.battery.load_energy(charger)
                )

        elif step_type == VehicleStateCategory.MOVE:
            # perform a MOVE step
            if self.route.is_empty():
                if self.has_passengers():
                    raise RouteStepError(f"{self} no default behavior with empty route and on-board passengers")
                else:
                    return self.transition(VehicleState.IDLE)
            else:
                return self._move(engine)

        else:
            raise NotImplementedError(f"Step function failed for undefined vehicle state category {step_type}")

    def battery_swap(self, battery: EnergySource) -> Vehicle:
        return self._replace(battery=battery)

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
