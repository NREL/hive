import logging
from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId, StationId, SimTime, ChargerId

log = logging.getLogger(__name__)


class ChargeQueueing(NamedTuple, VehicleState):
    """
    A vehicle tracks it's own place in a queue (Stations do not know about queues), and what guarantees
    a respect to vehicle queue positioning is their respective queue_times, which is used to sort all
    vehicles when applying the step_simulation_ops.perform_vehicle_state_updates.
    """
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId
    enqueue_time: SimTime

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
                entering a charge queueing state requires being at that station
                :param sim: the simulation state
                :param env: the simulation environment
                :return: an exception due to failure or an optional updated simulation
                """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_available_charger = station.available_chargers.get(self.charger_id, 0) > 0 if station else False
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif vehicle.geoid != station.geoid:
            return None, None
        elif has_available_charger:
            # maybe here instead, re-directed to ChargingStation?
            return None, None
        elif not vehicle.membership.valid_membership(station.membership):
            log.debug(f"vehicle {vehicle.id} and station {station.id} don't share a membership")
            return None, None
        else:
            updated_station = station.enqueue_for_charger(self.charger_id, vehicle.membership)
            error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
            if error:
                return error, None
            else:
                return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        remove agent from queue before exiting this state
        :param sim:
        :param env:
        :return:
        """
        station = sim.stations.get(self.station_id)
        if not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        else:

            updated_station = station.dequeue_for_charger(self.charger_id)
            error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
            if error:
                return error, None
            return None, updated_sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
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
            return station.available_chargers.get(self.charger_id, 0) > 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment) -> Tuple[
        Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        go idle if the station disappeared, otherwise begin charging
        :param sim:
        :param env:
        :return:
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_no_charger = station.available_chargers.get(self.charger_id, 0) == 0 if station else False
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif has_no_charger:
            return SimulationStateError(f"transitioning from queued to charging but no charger_id found"), None
        else:
            next_state = ChargingStation(self.vehicle_id, self.station_id, self.charger_id)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)

    def _perform_update(self, sim: 'SimulationState', env: Environment) -> Tuple[
        Optional[Exception], Optional['SimulationState']]:
        """
        similarly to the idle state, we incur an idling penalty here
        :param sim:
        :param env:
        :return:
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
            if not mechatronics:
                return SimulationStateError(f"cannot find {vehicle.mechatronics_id} in environment"), None
            less_energy_vehicle = mechatronics.idle(vehicle, sim.sim_timestep_duration_seconds)

            return simulation_state_ops.modify_vehicle(sim, less_energy_vehicle)
