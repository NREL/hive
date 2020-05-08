from __future__ import annotations

from typing import NamedTuple, Dict

from h3 import h3

from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.runner.environment import Environment
from hive.state.vehicle_state import VehicleState
from hive.state.vehicle_state.idle import Idle
from hive.util.typealiases import *
from hive.util.units import Kilometers, Currency


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

    # mechatronic properties
    mechatronics_id: MechatronicsId
    energy: Dict[EnergyType, float]

    # location
    link: Link

    # vehicle planning/operational properties
    vehicle_state: VehicleState

    # vehicle analytical properties
    balance: Currency = 0.0
    distance_traveled_km: Kilometers = 0.0

    @property
    def geoid(self):
        return self.link.start

    @classmethod
    def from_row(cls, row: Dict[str, str], road_network: RoadNetwork, environment: Environment) -> Vehicle:
        """
        reads a csv row from file to generate a Vehicle

        :param environment:
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
        else:
            try:
                vehicle_id = row['vehicle_id']
                lat = float(row['lat'])
                lon = float(row['lon'])
                mechatronics_id = row['mechatronics_id']

                mechatronics = environment.mechatronics.get(mechatronics_id)
                energy = mechatronics.initial_energy(float(row['initial_soc']))

                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                start_link = road_network.link_from_geoid(geoid)

                return Vehicle(
                    id=vehicle_id,
                    mechatronics_id=mechatronics_id,
                    energy=energy,
                    link=start_link,
                    vehicle_state=Idle(vehicle_id)
                )

            except ValueError:
                raise IOError(f"a numeric value could not be parsed from {row}")

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state},{self.energy_source})"

    def modify_energy(self, energy: Dict[EnergyType, float]) -> Vehicle:
        return self._replace(energy=energy)

    def modify_state(self, vehicle_state: VehicleState) -> Vehicle:
        return self._replace(vehicle_state=vehicle_state)

    def modify_link(self, link: Link) -> Vehicle:
        return self._replace(link=link)

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

    def tick_distance_traveled_km(self, delta_d_km: Kilometers) -> Vehicle:
        """
        adds distance to vehicle

        :param delta_d_km:
        :return:
        """
        return self._replace(distance_traveled_km=self.distance_traveled_km + delta_d_km)
