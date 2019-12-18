from typing import Tuple

from hive.dispatcher.instruction import Instruction
from hive.state.simulation_state import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.model.energy.charger import Charger
from hive.dispatcher.dispatcher import Dispatcher
from hive.util.helpers import H3Ops, DictOps
from hive.util.units import unit


class GreedyDispatcher(Dispatcher):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    # TODO: put these in init function to parameterize based on config file.
    LOW_SOC_TRESHOLD = 0.2
    MAX_IDLE_S = 600 * unit.seconds

    def generate_instructions(self, simulation_state: SimulationState, ) -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        """
        Generates instructions for a given simulation state.
        :param simulation_state:
        :return:
        """
        instructions = []

        vehicles_to_consider = simulation_state.vehicles.copy()
        stations_to_consider = simulation_state.stations.copy()

        low_soc_vehicles = [v for v in vehicles_to_consider.values()\
                            if v.energy_source.soc <= self.LOW_SOC_TRESHOLD\
                            and v.vehicle_state != VehicleState.DISPATCH_STATION]
        for veh in low_soc_vehicles:
            for _ in range(len(simulation_state.stations)):
                nearest_station = H3Ops.nearest_entity_point_to_point(geoid=veh.geoid,
                                                                      entities=stations_to_consider,
                                                                      entity_locations=simulation_state.s_locations,
                                                                      )
                if not nearest_station:
                    raise NotImplementedError('No stations found. Consider raising max_distance_km to higher threshold.')
                elif not nearest_station.has_available_charger(Charger.DCFC):
                    stations_to_consider = DictOps.remove_from_entity_dict(stations_to_consider, nearest_station.id)
                else:
                    break

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_STATION,
                                      location=nearest_station.geoid,
                                      station_id=nearest_station.id,
                                      charger=Charger.DCFC,
                                      )
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            _valid_states = [VehicleState.IDLE,
                             VehicleState.CHARGING_BASE,
                             VehicleState.RESERVE_BASE,
                             VehicleState.DISPATCH_BASE]
            if vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD and vehicle.vehicle_state in _valid_states:
                return True
            else:
                return False

        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity_point_to_point(geoid=request.origin,
                                                                  entities=vehicles_to_consider,
                                                                  entity_locations=simulation_state.v_locations,
                                                                  is_valid=_is_valid_for_dispatch,
                                                                  )
            if nearest_vehicle:
                instruction = Instruction(vehicle_id=nearest_vehicle.id,
                                          action=VehicleState.DISPATCH_TRIP,
                                          location=request.origin,
                                          request_id=request.id)
                instructions.append(instruction)
                vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, nearest_vehicle.id)

        stationary_vehicles = [v for v in vehicles_to_consider.values() if v.idle_time_s > self.MAX_IDLE_S]
        for veh in stationary_vehicles:
            nearest_base = H3Ops.nearest_entity_point_to_point(geoid=veh.geoid,
                                                               entities=simulation_state.bases,
                                                               entity_locations=simulation_state.b_locations,
                                                               )
            if not nearest_base:
                raise NotImplementedError('No bases found. Consider raising max_distance_km to higher threshold.')

            instruction = Instruction(vehicle_id=veh.id,
                                      action=VehicleState.DISPATCH_BASE,
                                      location=nearest_base.geoid)
            instructions.append(instruction)
            vehicles_to_consider = DictOps.remove_from_entity_dict(vehicles_to_consider, veh.id)

        def _should_base_charge(vehicle: Vehicle) -> bool:
            if vehicle.vehicle_state == VehicleState.RESERVE_BASE and not vehicle.energy_source.is_full():
                return True
            else:
                return False

        base_charge_vehicles = [v for v in vehicles_to_consider.values() if _should_base_charge(v)]
        for v in base_charge_vehicles:
            base_id = simulation_state.b_locations[v.geoid][0]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = Instruction(vehicle_id=v.id,
                                          action=VehicleState.CHARGING_BASE,
                                          station_id=base.station_id,
                                          charger=Charger.LEVEL_2,
                                          )
                instructions.append(instruction)

        return self, tuple(instructions)
