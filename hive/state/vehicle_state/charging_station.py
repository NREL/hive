from typing import Tuple, Optional, NamedTuple

from hive.model.energy.charger import Charger
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.vehicle_state_ops import charge
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state import VehicleState
from hive.runner.environment import Environment
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, VehicleId


class ChargingStation(NamedTuple, VehicleState):
    """
    a vehicle is charging at a station with a specific charger type
    """
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def enter(self,
              sim: 'SimulationState',
              env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        entering a charge event requires attaining a charger from the station
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        # ok, we want to enter a charging state.
        # we attempt to claim a charger from the station of this self.charger type
        # what if we can't? is that an Exception, or, is that simply rejected?
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif vehicle.geoid != station.geoid:
            return None, None
        else:
            updated_station = station.checkout_charger(self.charger)
            if not updated_station:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                if error:
                    return error, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def exit(self,
             sim: 'SimulationState',
             env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        exiting a charge event requires returning the charger to the station
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)

        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"vehicle {self.station_id} not found"), None
        else:
            updated_station = station.return_charger(self.charger)
            return simulation_state_ops.modify_station(sim, updated_station)

    def _has_reached_terminal_state_condition(self,
                                              sim: 'SimulationState',
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
            return vehicle.energy_source.is_at_ideal_energy_limit()

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        we default to idle, or reserve base if there is a base with stalls at the location
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState
        :param sim: the simulation state
        :param env: the simulation environment
        :param self.vehicle_id: the vehicle transitioning
        :return: an exception due to failure or an optional updated simulation
        """

        return charge(sim, env, self.vehicle_id, self.station_id, self.charger)
