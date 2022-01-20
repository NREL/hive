from __future__ import annotations

from typing import NamedTuple, Dict

import h3
import immutables

from hive.model.energy.energytype import EnergyType
from hive.model.membership import Membership
from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.runner.environment import Environment
from hive.state.driver_state.driver_state import DriverState
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.vehicle_state import VehicleState
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
    energy: immutables.Map[EnergyType, float]

    # location
    position: EntityPosition

    # vehicle planning/operational properties
    vehicle_state: VehicleState
    driver_state: DriverState
    total_seats: int
    # available_seats: int

    # vehicle analytical properties
    balance: Currency = 0.0
    distance_traveled_km: Kilometers = 0.0

    membership: Membership = Membership()

    @property
    def geoid(self):
        return self.position.geoid

    @classmethod
    def from_row(cls, row: Dict[str, str], road_network: RoadNetwork,
                 environment: Environment) -> Vehicle:
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
        elif 'mechatronics_id' not in row:
            raise IOError("cannot load a vehicle without a 'mechatronics_id'")
        else:
            try:
                vehicle_id = row['vehicle_id']
                lat = float(row['lat'])
                lon = float(row['lon'])
                mechatronics_id = row['mechatronics_id']

                mechatronics = environment.mechatronics.get(mechatronics_id)
                if not mechatronics:
                    found = set(environment.mechatronics.keys())
                    raise IOError(
                        f"was not able to find mechatronics '{mechatronics_id}' for vehicle {vehicle_id} in environment: found {found}"
                    )
                energy = mechatronics.initial_energy(float(row['initial_soc']))

                schedule_id = row.get(
                    'schedule_id'
                )  # if None, it signals an autonomous vehicle, otherwise, human with schedule
                home_base_id = row.get('home_base_id')
                if schedule_id and not schedule_id in environment.schedules.keys():
                    raise IOError(
                        f"was not able to find schedule '{schedule_id}' in environment for vehicle {vehicle_id}"
                    )
                allows_pooling = bool(
                    row['allows_pooling']) if row.get('allows_pooling') is not None else False
                available_seats = int(row.get('available_seats', 0))
                driver_state = DriverState.build(vehicle_id, schedule_id, home_base_id,
                                                 allows_pooling)

                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                start_position = road_network.position_from_geoid(geoid)

                return Vehicle(
                    id=vehicle_id,
                    mechatronics_id=mechatronics_id,
                    energy=energy,
                    position=start_position,
                    vehicle_state=Idle.build(vehicle_id),
                    driver_state=driver_state,
                    total_seats=available_seats,
                    # available_seats=available_seats
                )

            except ValueError as err:
                raise IOError(f"failure reading vehicle row {row}") from err

    def __repr__(self) -> str:
        return f"Vehicle({self.id},{self.vehicle_state})"

    def modify_energy(self, energy: immutables.Map[EnergyType, float]) -> Vehicle:
        """
        modify the energy level of the vehicle. should only be used by the mechatronics ops

        :param energy:
        :return:
        """
        return self._replace(energy=energy)

    def modify_vehicle_state(self, vehicle_state: VehicleState) -> Vehicle:
        """
        modify the state of the vehicle. should only be use by the vehicle state ops

        :param vehicle_state:
        :return:
        """
        return self._replace(vehicle_state=vehicle_state)

    def modify_driver_state(self, driver_state: DriverState) -> Vehicle:
        """
        modify the state of the vehicle's driver. should only be used by the driver state ops

        :param driver_state:
        :return:
        """
        return self._replace(driver_state=driver_state)

    def modify_position(self, position: EntityPosition) -> Vehicle:
        """
        modify the link of the vehicle. should only be used by the road network ops

        :param position:
        :return:
        """
        return self._replace(position=position)

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

    def set_membership(self, member_ids: Tuple[str, ...]) -> Vehicle:
        """
        sets the membership(s) of the vehicle

        :param member_ids: a Tuple containing updated membership(s) of the vehicle
        :return:
        """
        return self._replace(membership=Membership.from_tuple(member_ids))

    def add_membership(self, membership_id: MembershipId) -> Vehicle:
        """
        adds the membership to the vehicle

        :param membership_id: a membership for the vehicle
        :return:
        """
        updated_membership = self.membership.add_membership(membership_id)
        return self._replace(membership=updated_membership)
