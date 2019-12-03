from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.simulationstate.simulationstate import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.dispatcher.dispatcher import Dispatcher
from hive.model.request import RequestId
from hive.util.typealiases import GeoId
from hive.util.helpers import H3Ops, DictOps


class GreedyDispatcher(Dispatcher):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    def generate_instructions(self, simulation_state: SimulationState, ) -> Tuple[Instruction, ...]:
        """
        Generates instructions for a given simulation state.
        :param simulation_state:
        :return:
        """
        instructions = []

        vehicles_to_consider = simulation_state.vehicles.copy()

        low_soc_vehicles = [v for v in vehicles_to_consider.values() if v.energy_source.soc() <= 0.2]
        for veh in low_soc_vehicles:
            # TODO: if we have a low number of stations/bases, it might be quicker to just find the closest
            #  by computing the distance between all of them?
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_locations=simulation_state.s_locations,
                                                   max_k=1000)
            if not nearest_station:
                raise NotImplementedError("Unable to locate station. No default behavior for this edge case.")

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_STATION,
                                      location=nearest_station.geoid)
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            if vehicle.vehicle_state == VehicleState.IDLE and vehicle.energy_source.soc() > 0.2:
                return True
            else:
                return False

        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=vehicles_to_consider,
                                                   entity_locations=simulation_state.v_locations,
                                                   is_valid=_is_valid_for_dispatch,
                                                   max_k=100)
            if nearest_vehicle:
                instruction = Instruction(vehicle_id=nearest_vehicle.id,
                                          action=VehicleState.DISPATCH_TRIP,
                                          location=request.origin,
                                          request=request.id)
                instructions.append(instruction)
                vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, nearest_vehicle.id)

        stationary_vehicles = [v for v in vehicles_to_consider.values() if v.idle_time_steps > 600]
        for veh in stationary_vehicles:
            nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                entities=simulation_state.bases,
                                                entity_locations=simulation_state.b_locations,
                                                max_k=1000)
            if not nearest_base:
                raise NotImplementedError("Unable to locate base. No default behavior for this edge case.")

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_BASE,
                                      location=nearest_base.geoid)
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        return tuple(instructions)
