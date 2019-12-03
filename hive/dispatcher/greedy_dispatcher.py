from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.simulationstate.simulationstate import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.dispatcher.dispatcher import Dispatcher
from hive.model.request import RequestId
from hive.util.typealiases import GeoId
from hive.util.helpers import H3Ops


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

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            if vehicle.vehicle_state == VehicleState.IDLE and vehicle.battery.soc() > 0.2:
                return True
            else:
                return False

        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]

        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=simulation_state.vehicles,
                                                   entity_locations=simulation_state.v_locations,
                                                   is_valid=_is_valid_for_dispatch,
                                                   max_k=100)
            if nearest_vehicle:
                instruction = Instruction(vehicle_id=nearest_vehicle.id,
                                          action=VehicleState.DISPATCH_TRIP,
                                          location=request.origin,
                                          request=request.id)
                instructions.append(instruction)

        low_soc_vehicles = [v for v in simulation_state.vehicles.values() if v.battery.soc() <= 0.2]

        for veh in low_soc_vehicles:
            # TODO: if we have a low number of stations, it might be quicker to just find the closest
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

        return tuple(instructions)
