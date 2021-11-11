from __future__ import annotations

import logging
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING

from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.vehicle_state.vehicle_state import VehicleState
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

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.CHARGING_BASE

    def enter(self,
              sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        entering a charge event requires attaining a charger_id from the station situated at the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if not possible
        """
        base = sim.bases.get(self.base_id)
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not base:
            msg = f"base {self.base_id} not found"
            return SimulationStateError(msg), None
        elif not vehicle:
            msg = f"vehicle {self.vehicle_id} not found"
            return SimulationStateError(msg), None

        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        charger = env.chargers.get(self.charger_id)
        if not base.station_id:
            msg = f"base {self.base_id} is not co-located with a station"
            return SimulationStateError(msg), None
        elif not base.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} doesn't have access to base {base.id}"
            return SimulationStateError(msg), None
        elif not mechatronics.valid_charger(charger):
            msg = f"vehicle {vehicle.id} of type {vehicle.mechatronics_id} can't use charger {charger.id}"
            log.warning(msg)
            return SimulationStateError(msg), None
        else:
            station = sim.stations.get(base.station_id) if base.station_id else None
            if not station:
                msg = f"station {base.station_id} not found for vehicle {self.vehicle_id}"
                log.warning(msg)
                return SimulationStateError(msg), None
            else:
                updated_station = station.checkout_charger(self.charger_id)
                if not updated_station:
                    log.warning(f"vehicle {self.vehicle_id} can't checkout {self.charger_id} from {station.id}")
                    return None, None
                else:
                    error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                    if error:
                        log.warning(f"unable to update station {station.id}")
                        return error, None
                    else:
                        return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def exit(self,
             sim: SimulationState,
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

        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station for base {self.base_id} not found"), None
        else:
            error, updated_station = station.return_charger(self.charger_id)
            if error:
                return error, None
            return simulation_state_ops.modify_station(sim, updated_station)

    def _has_reached_terminal_state_condition(self,
                                              sim: SimulationState,
                                              env: Environment) -> bool:
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

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        we default to idle, or reserve base if there is a base with stalls at the location

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        next_state = ReserveBase(self.vehicle_id, self.base_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: SimulationState,
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
        if not station_id:
            return SimulationStateError(f"attempting to charge at base {base.id} which has no assoc. station_id"), None
        else:
            return charge(sim, env, self.vehicle_id, station_id, self.charger_id)
