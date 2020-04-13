from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId, StationId, SimTime
from hive.state.vehicle_state import VehicleState
from hive.model.energy.charger import Charger


class ChargeQueueing(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger
    enqueue_time: SimTime

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
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
            updated_station = station  # enqueue vehicle
            if not updated_station:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_station(sim, updated_station)
                if error:
                    return error, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        pass

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        pass

    def _perform_update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass
