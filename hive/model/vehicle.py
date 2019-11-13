from __future__ import annotations

import copy
from typing import NamedTuple, Tuple, Dict, Optional, Union

from hive.util.typealiases import *
from hive.util.tuple import head_tail
from hive.model.battery import Battery
from hive.model.engine import Engine
from hive.model.passenger import Passenger
from hive.roadnetwork.position import Position
from hive.model.request import Request
from hive.model.charger import Charger
from hive.model.vehiclestate import VehicleState, VehicleStateCategory
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
    route: Route = Route.empty()
    vehicle_state: VehicleState = VehicleState.IDLE
    # frozenmap implementation does not yet exist
    # https://www.python.org/dev/peps/pep-0603/
    passengers: Dict[PassengerId, Position] = {}
    distance_traveled: float = 0.0

    def has_passengers(self) -> bool:
        return len(self.passengers) > 0

    def has_route(self) -> bool:
        return bool(self.route.has_route())

    def plugged_in(self) -> bool:
        return self.plugged_in_charger is not None

    def add_passengers(self, new_passengers: Tuple[Passenger]) -> Vehicle:
        """
        loads some passengers onto this vehicle
        :param self:
        :param new_passengers: the set of passengers we want to add
        :return: the updated vehicle
        """
        updated_passengers = copy.copy(self.passengers)
        for passenger in new_passengers:
            updated_passengers[passenger.id] = passenger.destination
        return self._replace(passengers=updated_passengers)

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.battery})"

    def _move(self) -> Vehicle:
        # take one route step
        this_route_step, updated_route = self.route.step_route()
        this_fuel_usage = self.engine.route_step_fuel_cost(this_route_step)
        updated_battery = self.battery.use_fuel(this_fuel_usage)
        return self._replace(
            position=this_route_step.position,
            battery=updated_battery,
            route=updated_route,
            distance_traveled=self.distance_traveled + this_route_step.distance
        )

    def step(self) -> Vehicle:
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

        elif step_type == VehicleStateCategory.MOVE:
            # perform a MOVE step
            if self.route.is_empty():
                if self.has_passengers():
                    raise RouteStepError(f"{self} no default behavior with empty route and on-board passengers")
                else:
                    return self.transition_idle()
            else:
                return self._move()

        else:
            raise NotImplementedError(f"Step function failed for undefined vehicle state category {step_type}")

    def battery_swap(self, battery: Battery) -> Vehicle:
        return self._replace(battery=battery)


    """
    TRANSITION FUNCTIONS
    --------------------
    """

    def transition_idle(self) -> Union[Vehicle, None]:
        if self.has_passengers():
            return None
        else:
            return self._replace(
                route=Route.empty(),
                plugged_in_charger=None,
                vehicle_state=VehicleState.IDLE,
            )

    def transition_repositioning(self, route: Route) -> Union[Vehicle, None]:
        if self.has_passengers():
            return None
        elif self.vehicle_state == VehicleState.REPOSITIONING:
            return self
        else:
            return self._replace(
                route=route,
                plugged_in_charger=None,
                vehicle_state=VehicleState.REPOSITIONING,
            )

    def transition_dispatch_trip(self, dispatch_route: Route, service_route: Route) -> Union[Vehicle, None]:
        if self.has_passengers():
            # dynamic pooling -> remove this constraint? or, do we add a pooling vehicle state?
            return None

        # estimate the total fuel cost of dispatch + servicing, confirm SoC is good for trip
        dispatch_fuel_cost = self.engine.route_fuel_cost(dispatch_route)
        service_fuel_cost = self.engine.route_fuel_cost(service_route)
        estimated_fuel_effect = self.battery.load - (dispatch_fuel_cost + service_fuel_cost)
        fuel_lower_limit = self.battery.capacity * self.soc_lower_limit

        if estimated_fuel_effect < fuel_lower_limit:
            return None
        else:
            return self._replace(
                route=dispatch_route,
                plugged_in_charger=None,
                vehicle_state=VehicleState.DISPATCH_TRIP
            )

    def transition_servicing_trip(self, route: Route, request: Request) -> Union[Vehicle, None]:
        if self.vehicle_state == VehicleState.SERVICING_TRIP:
            return self
        elif self.has_passengers():
            return None
        else:
            fuel_estimate = self.engine.route_fuel_cost(route)
            battery_estimate = self.battery.use_fuel(fuel_estimate)
            resulting_soc = battery_estimate.soc()
            if resulting_soc < self.soc_lower_limit:
                return None
            else:
                return self._replace(
                    route=route,
                    plugged_in_charger=None,
                    vehicle_state=VehicleState.SERVICING_TRIP
                ).add_passengers(request.passengers)

    def transition_dispatch_station(self, route: Route) -> Union[Vehicle, None]:
        if self.vehicle_state == VehicleState.DISPATCH_STATION:
            return self
        if self.has_passengers():
            return None
        else:
            fuel_estimate = self.engine.route_fuel_cost(route)
            battery_estimate = self.battery.use_fuel(fuel_estimate)
            resulting_soc = battery_estimate.soc()
            if resulting_soc < self.soc_lower_limit:
                return None
            else:
                return self._replace(
                    route=route,
                    plugged_in_charger=None,
                    vehicle_state=VehicleState.DISPATCH_STATION
                )

    def transition_charging_station(self, charger: Charger) -> Union[Vehicle, None]:
        if self.vehicle_state == VehicleState.CHARGING_STATION:
            return self
        elif self.has_passengers():
            return None
        else:
            return self._replace(
                route=Route.empty(),
                vehicle_state=VehicleState.CHARGING_STATION,
                plugged_in_charger=charger
            )

    def transition_dispatch_base(self, route: Route) -> Union[Vehicle, None]:
        if self.vehicle_state == VehicleState.DISPATCH_BASE:
            return self
        elif self.has_passengers():
            return None
        else:
            return self._replace(
                vehicle_state=VehicleState.DISPATCH_BASE,
                plugged_in_charger=None,
                route=route
            )

    def transition_charging_base(self, charger: Charger) -> Union[Vehicle, None]:
        if self.vehicle_state == VehicleState.CHARGING_BASE:
            return self
        elif self.has_passengers():
            return None
        else:
            return self._replace(
                route=Route.empty(),
                vehicle_state=VehicleState.CHARGING_BASE,
                plugged_in_charger=charger
            )

    def transition_reserve_base(self) -> Union[Vehicle, None]:
        if self.has_passengers():
            return None
        else:
            return self._replace(
                route=Route.empty(),
                plugged_in_charger=None,
                vehicle_state=VehicleState.RESERVE_BASE,
            )
