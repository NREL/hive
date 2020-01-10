from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.manager.fleet_target import FleetStateTarget
from hive.state.simulation_state import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.model.energy.charger import Charger
from hive.dispatcher.dispatcher import Dispatcher
from hive.util.helpers import H3Ops
from hive.util.units import unit

import warnings


class ManagedDispatcher(Dispatcher):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """

    # TODO: put these in init function to parameterize based on config file.
    LOW_SOC_TRESHOLD = 0.2

    def generate_instructions(self,
                              simulation_state: SimulationState,
                              ) -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        instructions = []
        vehicle_ids_given_instructions = []

        # 1. find vehicles that require charging
        low_soc_vehicles = [v for v in simulation_state.vehicles.values()
                            if v.energy_source.soc <= self.LOW_SOC_TRESHOLD
                            and v.vehicle_state != VehicleState.DISPATCH_STATION]
        nearest_station = None
        for veh in low_soc_vehicles:
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_search=simulation_state.s_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=lambda s: s.has_available_charger(Charger.DCFC))
            if nearest_station:
                instruction = Instruction(vehicle_id=veh.id,
                                          action=VehicleState.DISPATCH_STATION,
                                          location=nearest_station.geoid,
                                          station_id=nearest_station.id,
                                          charger=Charger.DCFC,
                                          )

                instructions.append(instruction)
                vehicle_ids_given_instructions.append(veh.id)
            else:
                # user set the max search radius too low (should really be computed by
                # HIVE based on the RoadNetwork at initialization anyway)
                # also possible: no charging stations available. implement a queueing solution
                # for agents who could wait to charge
                continue

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            _valid_states = [VehicleState.IDLE,
                             VehicleState.CHARGING_BASE,
                             VehicleState.RESERVE_BASE,
                             VehicleState.DISPATCH_BASE]
            if vehicle.id not in vehicle_ids_given_instructions and \
                    vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD and \
                    vehicle.vehicle_state in _valid_states:
                return True
            else:
                return False

        # 2. find requests that need a vehicle
        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=simulation_state.vehicles,
                                                   entity_search=simulation_state.v_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=_is_valid_for_dispatch)
            if nearest_vehicle:
                instruction = Instruction(vehicle_id=nearest_vehicle.id,
                                          action=VehicleState.DISPATCH_TRIP,
                                          location=request.origin,
                                          request_id=request.id)
                instructions.append(instruction)
                vehicle_ids_given_instructions.append(nearest_vehicle.id)

        # 3. determine if we need to activate or deactivate vehicles based on the fleet manager targets.
        if 'ACTIVE' not in fleet_state_target:
            warnings.warn('fleet manager did not provide ACTIVE target, skipping fleet balance step.')
        else:
            active_target = fleet_state_target['ACTIVE']
            active_state_set = active_target.state_set
            vehicles = simulation_state.vehicles.values()
            n_active_vehicles = sum([1 for v in vehicles if v.vehicle_state in active_state_set])
            active_diff = n_active_vehicles - active_target.n_vehicles





        return self, tuple(instructions)
