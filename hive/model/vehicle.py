from __future__ import annotations

import copy
from typing import NamedTuple, Tuple, Dict, Optional

from hive.util.typealiases import *
from hive.model.battery import Battery
from hive.model.engine import Engine
from hive.model.passenger import Passenger
from hive.model.position import Position
from hive.model.request import Request
from hive.model.charger import Charger
from hive.physics.vehiclestate import VehicleState
from hive.roadnetwork.route import Route
from hive.util.exception import *


class Vehicle(NamedTuple):
    # fixed vehicle attributes
    id: VehicleId
    engine: Engine
    battery: Battery
    position: Position
    soc_upper_limit: Percentage = 1.0
    soc_lower_limit: Percentage = 0.0
    plugged_in_charger: Optional[Charger] = None
    route: Route = ()
    vehicle_state: VehicleState = VehicleState.IDLE
    # frozenmap implementation does not yet exist
    # https://www.python.org/dev/peps/pep-0603/
    passengers: Dict[Position, Passenger] = {}
    distance_traveled: float = 0.0

    def has_passengers(self) -> bool:
        return bool(self.passengers)

    def has_route(self) -> bool:
        return bool(self.route)

    def plugged_in(self) -> bool:
        return self.plugged_in_charger is not None

    def add_passengers(self, new_passengers: Tuple[Passenger]) -> Vehicle:
        """
        loads some passengers onto this vehicle

        :param new_passengers: the set of passengers we want to add
        :return: the updated vehicle
        """
        updated_passengers = copy.copy(self.passengers)
        for passenger in new_passengers:
            updated_passengers[passenger.destination] = passenger
        return self._replace(passengers=updated_passengers)

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.battery})"

    def step(self) -> Vehicle:
        """
        when an agent stays in the same vehicle state for two subsequent time steps,
        we perform their action in the transition.

        this may be charging, or, following a route.
        also may make a default state transition to IDLE if it is legal.
        :return:
        """
        if self.vehicle_state == VehicleState.IDLE or self.vehicle_state == VehicleState.RESERVE_BASE:
            return self  # noop
        elif self.vehicle_state == VehicleState.CHARGING_STATION or self.vehicle_state == VehicleState.CHARGING_BASE:
            if self.plugged_in_charger is None:
                raise StateOfChargeError(f"{self} cannot charge without a plugged-in charger")
            elif self.battery.soc() >= self.soc_upper_limit:
                # fall into IDLE state
                return self.transition_idle()
            else:
                # take one charging step
                return self._replace(
                    battery=self.battery.charge(self.plugged_in_charger)
                )
        elif self.route.is_empty():
            if self.has_passengers():
                raise RouteStepError(f"{self} no default behavior with empty route and on-board passengers")
            else:
                return self.transition_idle()
        else:
            # take one route step
            this_route_step, *updated_route = self.route.route
            this_fuel_usage = self.engine.route_step_fuel_cost(this_route_step)
            updated_battery = self.battery.use_fuel(this_fuel_usage)
            return self._replace(
                position=this_route_step.to_coordinate(),
                battery=updated_battery,
                route=updated_route,
                distance_traveled=self.distance_traveled + this_route_step.distance
            )

    def battery_swap(self, battery: Battery):
        return self._replace(battery=battery)

    """
    TRANSITION FUNCTIONS
    --------------------
    """

    def transition_idle(self) -> Vehicle:
        if self.has_passengers():
            raise StateTransitionError(f"{self} attempting to be idle but has passengers")
        else:
            return self._replace(
                route=Route.empty(),
                plugged_in_charger=None,
                vehicle_state=VehicleState.IDLE,
            ).step()

    def transition_repositioning(self, route: Route) -> Vehicle:
        if self.has_passengers():
            raise StateTransitionError(f"{self} attempting to be repositioning but has passengers")
        elif self.vehicle_state == VehicleState.REPOSITIONING:
            return self.step()
        else:
            return self._replace(
                route=route,
                plugged_in_charger=None,
                vehicle_state=VehicleState.REPOSITIONING,
            ).step()

    def transition_dispatch_trip(self, dispatch_route: Route, service_route: Route) -> Vehicle:
        if self.has_passengers():
            # dynamic pooling -> remove this constraint? or, do we add a pooling vehicle state?
            raise StateTransitionError(f"{self} attempting to dispatch to trip but has passengers")

        # estimate the total fuel cost of dispatch + servicing, confirm SoC is good for trip
        dispatch_fuel_cost = self.engine.route_fuel_cost(dispatch_route)
        service_fuel_cost = self.engine.route_fuel_cost(service_route)

        if dispatch_fuel_cost + service_fuel_cost > self.battery.load:
            raise StateTransitionError(f"{self} attempting to dispatch to trip but not enough fuel")
        else:
            return self._replace(
                route=dispatch_route,
                plugged_in_charger=None,
                vehicle_state=VehicleState.DISPATCH_TRIP
            ).step()

    def transition_servicing_trip(self, route: Route, request: Request) -> Vehicle:
        if self.vehicle_state == VehicleState.SERVICING_TRIP:
            return self.step()
        elif self.has_passengers:
            raise StateTransitionError(f"{self} bzz, HIVE does not yet support dynamic pooling")
        else:
            fuel_estimate = self.engine.route_fuel_cost(route)
            battery_estimate = self.battery.use_fuel(fuel_estimate)
            resulting_soc = battery_estimate.soc()
            if resulting_soc < self.soc_lower_limit:
                raise StateTransitionError(f"{self} servicing trip which would reduce fuel below soc_lower_limit")
            else:
                return self._replace(
                    route=route,
                    plugged_in_charger=None,
                    vehicle_state=VehicleState.SERVING_TRIP
                ).add_passengers(request.passengers).step()

    def transition_dispatch_station(self, route: Route) -> Vehicle:
        if self.vehicle_state == VehicleState.DISPATCH_STATION:
            return self.step()
        if self.has_passengers():
            raise StateTransitionError(f"{self} attempting to dispatch to station but has passengers")
        else:
            fuel_estimate = self.engine.route_fuel_cost(route)
            battery_estimate = self.battery.use_fuel(fuel_estimate)
            resulting_soc = battery_estimate.soc()
            if resulting_soc < self.soc_lower_limit:
                raise StateTransitionError(f"{self} servicing trip which would reduce fuel below soc_lower_limit")
            else:
                return self._replace(
                    route=route,
                    plugged_in_charger=None,
                    vehicle_state=VehicleState.DISPATCH_STATION
                ).step()

    def transition_charging_station(self, charger: Charger) -> Vehicle:
        if self.vehicle_state == VehicleState.CHARGING_STATION:
            return self.step()
        elif self.has_passengers():
            raise StateTransitionError(f"{self} attempting to be charging at station but has passengers")
        else:
            return self._replace(
                route=Route.empty(),
                vehicle_state=VehicleState.CHARGING_STATION,
                plugged_in_charger=charger
            ).step()

    def transition_dispatch_base(self, route: Route) -> Vehicle:
        if self.vehicle_state == VehicleState.DISPATCH_BASE:
            return self.step()
        elif self.has_passengers():
            raise StateTransitionError(f"{self} attempting to dispatch to base but has passengers")
        else:
            return self._replace(
                vehicle_state=VehicleState.DISPATCH_BASE,
                plugged_in_charger=None,
                route=route
            ).step()

    def transition_charging_base(self, charger: Charger) -> Vehicle:
        if self.vehicle_state == VehicleState.CHARGING_BASE:
            return self.step()
        elif self.has_passengers():
            raise StateTransitionError(f"{self} attempting to be charging at base but has passengers")
        else:
            return self._replace(
                route=Route.empty(),
                vehicle_state=VehicleState.CHARGING_BASE,
                plugged_in_charger=charger
            ).step()

    def transition_reserve_base(self) -> Vehicle:
        if self.has_passengers():
            raise StateTransitionError(f"{self} attempting to reserve at base but has passengers")
        else:
            return self._replace(
                route=Route.empty(),
                plugged_in_charger=None,
                vehicle_state=VehicleState.RESERVE_BASE,
            ).step()