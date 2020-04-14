from __future__ import annotations

from typing import NamedTuple, Dict

from h3 import h3

from hive.model.energy.energysource import EnergySource
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import RouteTraversal
from hive.model.vehicle.vehicle_type import VehicleType
from hive.runner.environment import Environment
from hive.state.vehicle_state import VehicleState
from hive.state.vehicle_state.idle import Idle
from hive.util.typealiases import *
from hive.util.units import Kilometers, Seconds, Currency


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
    :param link: The current location of the vehicle
    :type link: :py:obj:`Link`
    :param operating_cost_km: the operating cost per kilometer of this vehicle
    :type operating_cost_km: :py:obj:`Currency`
    :param route: The route of the vehicle. Could be empty.
    :type route: :py:obj:`Route`
    :param vehicle_state: The state that the vehicle is in.
    :type vehicle_state: :py:obj:`VehicleState`
    :param passengers: A map of passengers that are in the vehicle. Could be empty
    :type passengers: :py:obj:`Dict[PasengerId, Passengers]`
    :param charger_intent: The charger type a vehicle intends to plug into.
    :type charger_intent: :py:obj:`Optional[Charger]`
    :param idle_time_s: A counter to track how long the vehicle has been idle.
    :type idle_time_s: :py:obj:`seconds`
    :param distance_traveled: A accumulator to track how far a vehicle has traveled.
    :type distance_traveled_km: :py:obj:`kilometers`
    """
    # core vehicle properties
    id: VehicleId
    powertrain_id: PowertrainId
    powercurve_id: PowercurveId
    energy_source: EnergySource
    link: Link
    operating_cost_km: Currency

    # vehicle planning/operational properties
    vehicle_state: VehicleState

    # vehicle analytical properties
    balance: Currency = 0.0
    idle_time_seconds: Seconds = 0
    distance_traveled_km: Kilometers = 0.0

    @property
    def geoid(self):
        return self.link.start

    @classmethod
    def from_row(cls, row: Dict[str, str], road_network: RoadNetwork, env: Environment) -> Vehicle:
        """
        reads a csv row from file to generate a Vehicle

        :param row: a row of a .csv which matches hive.util.pattern.vehicle_regex.
        this string will be stripped of whitespace characters (no spaces allowed in names!)
        :param road_network: the road network, used to find the vehicle's location in the sim
        :param env: the scenario environment
        :return: a vehicle, or, an IOError if failure occurred.
        """

        if 'vehicle_id' not in row:
            raise IOError("cannot load a vehicle without a 'vehicle_id'")
        elif 'lat' not in row:
            raise IOError("cannot load a vehicle without a 'lat'")
        elif 'lon' not in row:
            raise IOError("cannot load a vehicle without a 'lon'")
        else:
            try:
                vehicle_id = row['vehicle_id']
                lat = float(row['lat'])
                lon = float(row['lon'])
                vehicle_type_id = row['vehicle_type_id']
                vehicle_type: VehicleType = env.vehicle_types.get(vehicle_type_id)
                if vehicle_type is None:
                    file = env.config.io.vehicle_types_file
                    raise IOError(f"cannot find vehicle_type {vehicle_type_id} in provided vehicle_type_file {file}")
                powertrain_id = vehicle_type.powertrain_id
                powercurve_id = vehicle_type.powercurve_id
                energy_type = env.energy_types.get(powercurve_id)
                capacity = vehicle_type.capacity_kwh
                max_charge_acceptance = vehicle_type.max_charge_acceptance
                operating_cost_km = vehicle_type.operating_cost_km
                initial_soc = float(row['initial_soc'])

                if not 0.0 <= initial_soc <= 1.0:
                    raise IOError(f"initial soc for vehicle: '{initial_soc}' must be in range [0,1]")

                energy_source = EnergySource.build(powercurve_id,
                                                   energy_type,
                                                   capacity,
                                                   max_charge_acceptance,
                                                   initial_soc)

                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                start_link = road_network.link_from_geoid(geoid)

                return Vehicle(
                    id=vehicle_id,
                    powertrain_id=powertrain_id,
                    powercurve_id=powercurve_id,
                    energy_source=energy_source,
                    link=start_link,
                    operating_cost_km=operating_cost_km,
                    vehicle_state=Idle(vehicle_id)
                )

            except ValueError:
                raise IOError(f"a numeric value could not be parsed from {row}")

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.energy_source})"

    def modify_state(self, vehicle_state: VehicleState) -> Vehicle:
        return self._replace(vehicle_state=vehicle_state)

    def modify_link(self, link: Link) -> Vehicle:
        return self._replace(link=link)

    def apply_route_traversal(self,
                              traverse_result: RouteTraversal,
                              road_network: RoadNetwork,
                              env: Environment) -> Vehicle:

        powertrain = env.powertrains.get(self.powertrain_id)
        experienced_route = traverse_result.experienced_route
        energy_used = powertrain.energy_cost(experienced_route)
        step_distance_km = traverse_result.traversal_distance_km
        remaining_route = traverse_result.remaining_route

        # todo: we allow the agent to traverse only bounded by time, not energy;
        #   so, it is possible for the vehicle to travel farther in a time step than
        #   they have fuel to travel. this can create an error on the location of
        #   any agents at the time step where they run out of fuel. feels like an
        #   acceptable edge case but we could improve. rjf 20200309

        updated_energy_source = self.energy_source.use_energy(energy_used)
        less_energy_vehicle = self.modify_energy_source(
            energy_source=updated_energy_source)  # .assign_route(remaining_route)

        if not remaining_route:
            geoid = experienced_route[-1].end
            link = road_network.link_from_geoid(geoid)
            return less_energy_vehicle._replace(
                link=link,
                distance_traveled_km=self.distance_traveled_km + step_distance_km,
            )
        else:
            return less_energy_vehicle._replace(
                link=remaining_route[0],
                distance_traveled_km=self.distance_traveled_km + step_distance_km,
            )

    def modify_energy_source(self, energy_source: EnergySource) -> Vehicle:
        """
        Replaces the vehicle energy source with a new energy source.

        :param energy_source: the new energy source
        :return: the updated vehicle
        """
        return self._replace(energy_source=energy_source)

    def send_payment(self, amount: Currency) -> Vehicle:
        """
        updates the Vehicle's balance based on sending a payment
        :param amount: the amount to pay
        :return: the updated Vehicle
        """
        return self._replace(balance=self.balance - amount)

    def receive_payment(self, amount: Currency) -> Vehicle:
        """
        updates the Vehicle's balance based on receiving a payment
        :param amount: the amount to be paid
        :return: the updated Vehicle
        """
        return self._replace(balance=self.balance + amount)
