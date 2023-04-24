from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from nrel.hive.model.sim_time import SimTime
from nrel.hive.runner.environment import Environment
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.state.vehicle_state.vehicle_state import (
    VehicleState,
    VehicleStateInstanceId,
)
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.exception import SimulationStateError
from nrel.hive.util.typealiases import VehicleId, StationId, ChargerId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargeQueueing(VehicleState):
    """
    A vehicle tracks it's own place in a queue (Stations do not know about queues), and what guarantees
    a respect to vehicle queue positioning is their respective queue_times, which is used to sort all
    vehicles when applying the step_simulation_ops.perform_vehicle_state_updates.
    """

    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId
    enqueue_time: SimTime

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(
        cls,
        vehicle_id: VehicleId,
        station_id: StationId,
        charger_id: ChargerId,
        enqueue_time: SimTime,
    ) -> ChargeQueueing:
        return ChargeQueueing(
            vehicle_id=vehicle_id,
            station_id=station_id,
            charger_id=charger_id,
            enqueue_time=enqueue_time,
            instance_id=uuid4(),
        )

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.CHARGE_QUEUEING

    def enter(
        self, sim: SimulationState, env: "Environment"
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        entering a charge queueing state requires being at that station

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_available_charger = (
            station.has_available_charger(self.charger_id) if station is not None else False
        )
        context = f"vehicle {self.vehicle_id} entering queueing at station {self.station_id}"
        if not vehicle:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        elif not station:
            return (
                SimulationStateError(f"station not found; context: {context}"),
                None,
            )
        elif vehicle.geoid != station.geoid:
            return None, None
        elif has_available_charger:
            # maybe here instead, re-directed to ChargingStation?
            return None, None
        elif not station.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle doesn't have access to station; context: {context}"
            return SimulationStateError(msg), None
        else:
            err1, updated_station = station.enqueue_for_charger(self.charger_id)
            if err1 is not None:
                return err1, None
            elif updated_station is None:
                return None, None
            else:
                err2, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                if err2 is not None:
                    response = SimulationStateError(
                        f"failure during ChargeQueueing.enter for vehicle {self.vehicle_id}"
                    )
                    response.__cause__ = err2
                    return response, None
                else:
                    if updated_sim is None:
                        return Exception("sim was none when error was not none"), None
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(
        self, sim: SimulationState, env: "Environment"
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def exit(
        self,
        next_state: VehicleState,
        sim: SimulationState,
        env: "Environment",
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        remove agent from queue before exiting this state

        :param sim:
        :param env:
        :return:
        """
        station = sim.stations.get(self.station_id)
        context = f"vehicle {self.vehicle_id} exiting queueing at station {self.station_id}"
        if not station:
            return (
                SimulationStateError(f"station not found; context: {context}"),
                None,
            )
        else:
            error, updated_station = station.dequeue_for_charger(self.charger_id)
            if error is not None:
                return error, None
            elif updated_station is None:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                if error:
                    response = SimulationStateError(
                        f"failure during ChargeQueueing.exit for vehicle {self.vehicle_id}"
                    )
                    response.__cause__ = error
                    return response, None
                return None, updated_sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        vehicle has reached a terminal state if the station disappeared
        or if it has at least one charger_id of the correct type

        :param sim:
        :param env:
        :return:
        """
        station = sim.stations.get(self.station_id)
        if not station:
            return True
        else:
            return station.has_available_charger(self.charger_id)

    def _default_terminal_state(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        gets the default terminal state for this state which should be transitioned to
        once it reaches the end of the current task.
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception or the default VehicleState
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_available_charger = (
            station.has_available_charger(self.charger_id) if station is not None else False
        )
        context = f"vehicle {self.vehicle_id} entering default terminal state for charge queueing at station {self.station_id}"
        if not vehicle:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        elif not station:
            return (
                SimulationStateError(f"station not found; context: {context}"),
                None,
            )
        elif not has_available_charger:
            return (
                SimulationStateError(f"no charger is available; context: {context}"),
                None,
            )
        else:
            next_state = ChargingStation.build(self.vehicle_id, self.station_id, self.charger_id)
            return None, next_state

    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        similarly to the idle state, we incur an idling penalty here

        :param sim:
        :param env:
        :return:
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        context = f"vehicle {self.vehicle_id} performing update for charge queueing at station {self.station_id}"
        if not vehicle:
            return (
                SimulationStateError(f"vehicle {self.vehicle_id} not found; context: {context}"),
                None,
            )
        else:
            mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
            if not mechatronics:
                return (
                    SimulationStateError(
                        f"cannot find {vehicle.mechatronics_id} in environment; context: {context}"
                    ),
                    None,
                )
            less_energy_vehicle = mechatronics.idle(vehicle, sim.sim_timestep_duration_seconds)

            return simulation_state_ops.modify_vehicle(sim, less_energy_vehicle)
