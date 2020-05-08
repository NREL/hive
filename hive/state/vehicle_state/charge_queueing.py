from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.util import SECONDS_TO_HOURS
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId, StationId, SimTime
from hive.state.vehicle_state import VehicleState, ChargingStation
from hive.model.energy.charger import Charger


class ChargeQueueing(NamedTuple, VehicleState):
    """
    A vehicle tracks it's own place in a queue (Stations do not know about queues), and what guarantees
    a respect to vehicle queue positioning is their respective queue_times, which is used to sort all
    vehicles when applying the step_simulation_ops.perform_vehicle_state_updates.
    """
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger
    enqueue_time: SimTime

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
                entering a charge queueing state requires being at that station
                :param sim: the simulation state
                :param env: the simulation environment
                :return: an exception due to failure or an optional updated simulation
                """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_available_charger = station.available_chargers.get(self.charger, 0) > 0 if station else False
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif vehicle.geoid != station.geoid:
            return None, None
        elif has_available_charger:
            # maybe here instead, re-directed to ChargingStation?
            return None, None
        else:
            return VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        the simulation state does not need modification in order to exit a charge queueing state (NOOP)
        :param sim:
        :param env:
        :return:
        """
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        vehicle has reached a terminal state if the station disappeared
        or if it has at least one charger of the correct type
        :param sim:
        :param env:
        :return:
        """
        station = sim.stations.get(self.station_id)
        if not station:
            return True
        else:
            return station.available_chargers.get(self.charger, 0) > 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        go idle if the station disappeared, otherwise begin charging
        :param sim:
        :param env:
        :return:
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        has_no_charger = station.available_chargers.get(self.charger, 0) == 0 if station else False
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif has_no_charger:
            return SimulationStateError(f"transitioning from queued to charging but no charger found"), None
        else:
            next_state = ChargingStation(self.vehicle_id, self.station_id, self.charger)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)

    def _perform_update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
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
            less_energy_vehicle = mechatronics.idle(vehicle, sim.sim_timestep_duration_seconds)

            # updated_idle_duration = (self.idle_duration + sim.sim_timestep_duration_seconds)
            # updated_state = self._replace(idle_duration=updated_idle_duration)
            # updated_vehicle = less_energy_vehicle.modify_state(updated_state)

            return simulation_state_ops.modify_vehicle(sim, less_energy_vehicle)

