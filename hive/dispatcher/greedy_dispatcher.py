from typing import Tuple, NamedTuple

from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.model.instruction import *
from hive.model.energy.charger import Charger
from hive.model.vehicle import Vehicle
from hive.model.vehiclestate import VehicleState
from hive.state.simulation_state import SimulationState
from hive.util.helpers import H3Ops
from hive.util.typealiases import SimTime


class GreedyDispatcher(NamedTuple, DispatcherInterface):
    """
    A class that computes instructions for the fleet based on a given simulation state.
    """

    # TODO: put these in init function to parameterize based on config file.
    LOW_SOC_TRESHOLD: float = 0.2
    MAX_IDLE_S: SimTime = 600

    def generate_instructions(self,
                              simulation_state: SimulationState,
                              ) -> Tuple[DispatcherInterface, Tuple[Instruction, ...]]:
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
                instruction = DispatchStationInstruction(
                    vehicle_id=veh.id,
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
            _valid_states = (VehicleState.IDLE,
                             VehicleState.CHARGING_BASE,
                             VehicleState.RESERVE_BASE,
                             VehicleState.DISPATCH_BASE)
            return bool(vehicle.id not in vehicle_ids_given_instructions and
                        vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD and
                        vehicle.vehicle_state in _valid_states)

        # 2. find requests that need a vehicle
        unassigned_requests = [r for r in simulation_state.requests.values() if not r.dispatched_vehicle]
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=simulation_state.vehicles,
                                                   entity_search=simulation_state.v_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=_is_valid_for_dispatch)
            if nearest_vehicle:
                instruction = DispatchTripInstruction(
                    vehicle_id=nearest_vehicle.id,
                    request_id=request.id,
                )
                instructions.append(instruction)
                vehicle_ids_given_instructions.append(nearest_vehicle.id)

        stationary_vehicles = [v for v in simulation_state.vehicles.values() if
                               v.idle_time_seconds > self.MAX_IDLE_S and v.id not in vehicle_ids_given_instructions]

        # 3. Send idle vehicles back to the base
        for veh in stationary_vehicles:
            nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                entities=simulation_state.bases,
                                                entity_search=simulation_state.b_search,
                                                sim_h3_search_resolution=simulation_state.sim_h3_search_resolution)
            if nearest_base:
                instruction = DispatchBaseInstruction(
                    vehicle_id=veh.id,
                    destination=nearest_base.geoid,
                )
                instructions.append(instruction)
                vehicle_ids_given_instructions.append(veh.id)
            else:
                # user set the max search radius too low
                continue

        def _should_base_charge(vehicle: Vehicle) -> bool:
            return bool(vehicle.vehicle_state == VehicleState.RESERVE_BASE and not
                        vehicle.energy_source.is_at_ideal_energy_limit())

        # 4. charge vehicles sitting at base
        base_charge_vehicles = [v for v in simulation_state.vehicles.values() if
                                v.id not in vehicle_ids_given_instructions and _should_base_charge(v)]
        for v in base_charge_vehicles:
            base_id = simulation_state.b_locations[v.geoid][0]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = ChargeBaseInstruction(
                    vehicle_id=v.id,
                    station_id=base.station_id,
                    charger=Charger.LEVEL_2,
                )
                instructions.append(instruction)
                vehicle_ids_given_instructions.append(v.id)

        return self, tuple(instructions)
