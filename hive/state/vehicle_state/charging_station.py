from __future__ import annotations

import logging
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING
import uuid

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state.vehicle_state_ops import charge
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, VehicleId, ChargerId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


class ChargingStation(NamedTuple, VehicleState):
    """
    a vehicle is charging at a station with a specific charger_id type
    """
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, station_id: StationId,
              charger_id: ChargerId) -> ChargingStation:
        """
        build a charging station state

        :param vehicle_id: the vehicle id
        :param station_id: the station id
        :param charger_id: the charger id

        :return: a charging station state 
        """
        return cls(vehicle_id=vehicle_id,
                   station_id=station_id,
                   charger_id=charger_id,
                   instance_id=uuid.uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.CHARGING_STATION

    def enter(self, sim: 'SimulationState',
              env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        entering a charge event requires attaining a charger_id from the station

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """

        self = self._replace(instance_id=uuid.uuid4())

        # ok, we want to enter a charging state.
        # we attempt to claim a charger_id from the station of this self.charger_id type
        # what if we can't? is that an Exception, or, is that simply rejected?
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        context = f"vehicle {self.vehicle_id} entering charging station state at station {self.station_id} with charger {self.charger_id}"
        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not station:
            return SimulationStateError(f"station not found; context: {context}"), None

        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        charger_err, charger = station.get_charger_instance(self.charger_id)
        if mechatronics is None:
            return SimulationStateError(f"unknown mechatronics id {vehicle.mechatronics_id}"), None
        if vehicle.geoid != station.geoid:
            return None, None
        elif not station.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} doesn't have access to station {station.id}"
            return SimulationStateError(msg), None
        elif charger_err is not None:
            return charger_err, None
        elif not mechatronics.valid_charger(charger):
            msg = f"vehicle {vehicle.id} of type {vehicle.mechatronics_id} can't use charger {charger.id}"
            return SimulationStateError(msg), None
        else:
            error, updated_station = station.checkout_charger(self.charger_id)
            if error is not None:
                return error, None
            elif updated_station is None:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                if error:
                    response = SimulationStateError(
                        f"failure during ChargingStation.enter for vehicle {self.vehicle_id}")
                    response.__cause__ = error
                    return response, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(self, sim: 'SimulationState',
               env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def exit(self, next_state: VehicleState, sim: 'SimulationState',
             env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        exiting a charge event requires returning the charger_id to the station

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)

        context = f"vehicle {self.vehicle_id} exiting charging station state at station {self.station_id} with charger {self.charger_id}"
        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not station:
            return SimulationStateError(f"station not found; context: {context}"), None
        else:
            error, updated_station = station.return_charger(self.charger_id)
            if error:
                response = SimulationStateError(
                    f"failure returning charger during ChargingStation.exit for vehicle {self.vehicle_id} at station {self.station_id}")
                response.__cause__ = error
                return response, None
            return simulation_state_ops.modify_station(sim, updated_station)

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState',
                                              env: Environment) -> bool:
        """
        test if charging is finished

        :param sim: the simulation state
        :param env: the simulation environment
        :return: True if the vehicle is fully charged
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not vehicle:
            return False
        else:
            mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
            return mechatronics.is_full(vehicle)

    def _default_terminal_state(
            self, sim: 'SimulationState',
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        next_state = Idle.build(self.vehicle_id)
        return None, next_state

    def _perform_update(
            self, sim: 'SimulationState',
            env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState

        :param sim: the simulation state
        :param env: the simulation environment
        :param self.vehicle_id: the vehicle transitioning
        :return: an exception due to failure or an optional updated simulation
        """

        return charge(sim, env, self.vehicle_id, self.station_id, self.charger_id)
