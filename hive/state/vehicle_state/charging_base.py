from __future__ import annotations

import logging
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING
from uuid import uuid4

from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state.vehicle_state_ops import charge
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import BaseId, VehicleId, ChargerId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


class ChargingBase(NamedTuple, VehicleState):
    """
    a vehicle is charging at a base with a specific charger_id type
    """

    vehicle_id: VehicleId
    base_id: BaseId
    charger_id: ChargerId

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId, base_id: BaseId, charger_id: ChargerId) -> ChargingBase:
        return ChargingBase(vehicle_id, base_id, charger_id, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.CHARGING_BASE

    def enter(self, sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        entering a charge event requires attaining a charger_id from the station situated at the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if not possible
        """

        
        vehicle = sim.vehicles.get(self.vehicle_id)
        base = sim.bases.get(self.base_id)
        station_id = base.station_id if base is not None and base.station_id is not None else None
        station = sim.stations.get(station_id) if station_id is not None else None
        mechatronics = env.mechatronics.get(vehicle.mechatronics_id) if vehicle is not None else None
        context = f"vehicle {self.vehicle_id} entering charging base state at base {self.base_id} with charger {self.charger_id}"
        if not vehicle:
            msg = f"vehicle not found; context {context}"
            return SimulationStateError(msg), None
        elif not base:
            msg = f"base not found; context: {context}"
            return SimulationStateError(msg), None
        elif not base.station_id:
            msg = f"base does not have attached station; context: {context}"
            return SimulationStateError(msg), None
        elif not station:
            msg = f"station {base.station_id} at base not found; context: {context}"
            return SimulationStateError(msg), None  
        elif not mechatronics:
            msg = f"vehicle {vehicle.id} has invalid mechatronics id; context: {context}"
            return SimulationStateError(msg), None  
        elif not base.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle doesn't have access to base; context: {context}"
            return SimulationStateError(msg), None
        else:
            # actually claim the parking stall
            updated_base = base.checkout_stall()
            if not updated_base:
                # no stall available for charging
                return None, None
            else:
                # grab the charger from the station
                charger_err, charger = station.get_charger_instance(self.charger_id)
                if charger_err is not None:
                    return charger_err, None  
                elif not mechatronics.valid_charger(charger):
                    msg = f"vehicle of type {vehicle.mechatronics_id} can't use charger; context: {context}"
                    return SimulationStateError(msg), None
                else:
                    # check out this charger from the station
                    error, updated_station = station.checkout_charger(self.charger_id)
                    if error is not None:
                        return error, None
                    elif not updated_station:
                        log.warning(
                            f"vehicle {self.vehicle_id} can't checkout {self.charger_id} from {station.id}"
                        )
                        return None, None                    
                    else:
                        # update the base + station state
                        err1, sim2 = simulation_state_ops.modify_base(sim, updated_base)
                        if err1:
                            response = SimulationStateError(
                                f"failure during ChargingBase.enter for vehicle {self.vehicle_id}")
                            response.__cause__ = err1
                            return response, None
                        else:
                            err2, sim3 = simulation_state_ops.modify_station(sim2, updated_station)
                            if err2:
                                response = SimulationStateError(
                                    f"failure during ChargingBase.enter for vehicle {self.vehicle_id}"
                                )
                                response.__cause__ = err2
                                return response, None
                            else:
                                return VehicleState.apply_new_vehicle_state(sim3, self.vehicle_id, self)

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        exiting a charge event requires returning the charger_id to the station at the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        base = sim.bases.get(self.base_id)
        station = sim.stations.get(base.station_id) if base.station_id else None
        context = f"vehicle {self.vehicle_id} exiting charging base state at base {self.base_id}"

        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not station:
            return (
                SimulationStateError(f"station for base not found; context: {context}"),
                None,
            )
        else:
            err1, updated_base = base.return_stall()
            if err1:
                response = SimulationStateError(
                    f"failure during ChargingBase.exit for vehicle {self.vehicle_id}")
                response.__cause__ = err1
                return response, None
            else:
                err2, sim2 = simulation_state_ops.modify_base(sim, updated_base)
                if err2:
                    response = SimulationStateError(
                        f"failure during ChargingBase.exit for vehicle {self.vehicle_id}")
                    response.__cause__ = err2
                    return response, None
                else:
                    err3, updated_station = station.return_charger(self.charger_id)
                    if err3:
                        response = SimulationStateError(
                            f"failure during ChargingBase.exit for vehicle {self.vehicle_id}")
                        response.__cause__ = err3
                        return response, None
                    return simulation_state_ops.modify_station(sim2, updated_station)

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        test if charging is finished

        :param sim: the simulation state
        :param env: the simulation environment
        :return: True if the vehicle is fully charged
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        if not vehicle:
            return False
        else:
            return mechatronics.is_full(vehicle)

    def _default_terminal_state(
            self, sim: SimulationState,
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        next_state = ReserveBase.build(self.vehicle_id, self.base_id)
        return None, next_state

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState

        :param sim: the simulation state
        :param env: the simulation environment
        :param self.vehicle_id: the vehicle transitioning
        :return: an exception due to failure or an optional updated simulation
        """
        base = sim.bases.get(self.base_id)
        station_id = base.station_id if base else None

        context = f"vehicle {self.vehicle_id} performing update for charging base state at base {self.base_id}"
        if not station_id:
            return (
                SimulationStateError(
                    f"attempting to charge at base which has no assoc. station_id; context: {context}"
                ),
                None,
            )
        else:
            return charge(sim, env, self.vehicle_id, station_id, self.charger_id)
