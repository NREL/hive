from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.state.simulation_state import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.model.energy.charger import Charger
from hive.dispatcher.dispatcher import Dispatcher
from hive.util.helpers import H3Ops, DictOps


class GreedyDispatcher(Dispatcher):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    # TODO: put these in init function to parameterize based on config file.
    LOW_SOC_TRESHOLD = 0.2
    MAX_IDLE_S = 600

    def generate_instructions(self, simulation_state: SimulationState, ) -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        """
        Generates instructions for a given simulation state.
        :param simulation_state:
        :return:
        """
        instructions = []

        vehicles_to_consider = simulation_state.vehicles.copy()

        low_soc_vehicles = [v for v in vehicles_to_consider.values() if v.energy_source.soc <= self.LOW_SOC_TRESHOLD]
        for veh in low_soc_vehicles:
            # TODO: if we have a low number of stations/bases, it might be quicker to just find the closest
            #  by computing the distance between all of them?
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_locations=simulation_state.s_locations,
                                                   max_distance_km=1,
                                                   )
            if not nearest_station:
                raise NotImplementedError('No stations found. Consider raising max_distance_km to higher threshold.')

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_STATION,
                                      location=nearest_station.geoid,
                                      station_id=nearest_station.id,
                                      charger=Charger.DCFC,
                                      )
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            if vehicle.vehicle_state == VehicleState.IDLE and vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD:
                return True
            else:
                return False

        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=vehicles_to_consider,
                                                   entity_locations=simulation_state.v_locations,
                                                   is_valid=_is_valid_for_dispatch,
                                                   max_distance_km=0.5)
            if nearest_vehicle:
                instruction = Instruction(vehicle_id=nearest_vehicle.id,
                                          action=VehicleState.DISPATCH_TRIP,
                                          location=request.origin,
                                          request_id=request.id)
                instructions.append(instruction)
                vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, nearest_vehicle.id)

        stationary_vehicles = [v for v in vehicles_to_consider.values() if v.idle_time_s > self.MAX_IDLE_S]
        for veh in stationary_vehicles:
            nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                entities=simulation_state.bases,
                                                entity_locations=simulation_state.b_locations,
                                                max_distance_km=1)
            if not nearest_base:
                raise NotImplementedError('No bases found. Consider raising max_distance_km to higher threshold.')

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_BASE,
                                      location=nearest_base.geoid)
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        return self, tuple(instructions)
