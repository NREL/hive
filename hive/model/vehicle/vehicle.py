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
    :param mechatronics_id: A id of the mechatronics component of the vehicle.
    :param energy: The energy of the vehicle
    :param link: The current location of the vehicle
    :param vehicle_state: The state that the vehicle is in.
    :param balance: How much revenue the vehicle has accumulated.
    :param distance_traveled_km: A accumulator to track how far a vehicle has traveled.
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
                if not mechatronics:
                    raise IOError(f"was not able to find mechatronics {mechatronics_id} in environment")
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
        return f"Vehicle({self.id},{self.vehicle_state})"

    def modify_energy(self, energy: Dict[EnergyType, float]) -> Vehicle:
        """
        modify the energy level of the vehicle. should only be used by the mechatronics ops
        :param energy:
        :return:
        """
        return self._replace(energy=energy)

    def modify_state(self, vehicle_state: VehicleState) -> Vehicle:
        """
        modify the state of the vehicle. should only be use by the vehicle state ops
        :param vehicle_state:
        :return:
        """
        return self._replace(vehicle_state=vehicle_state)

    def modify_link(self, link: Link) -> Vehicle:
        """
        modify the link of the vehicle. should only be used by the road network ops
        :param link:
        :return:
        """
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
