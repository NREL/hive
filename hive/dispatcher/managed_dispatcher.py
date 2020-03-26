from __future__ import annotations

from typing import Tuple, NamedTuple, Dict, TYPE_CHECKING

from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.model.energy.charger import Charger
from hive.model.instruction import *
from hive.state.vehicle_state import *
from hive.util.helpers import H3Ops

if TYPE_CHECKING:
    from hive.model.vehicle import Vehicle
    from hive.util.typealiases import SimTime, VehicleId, Report


class ManagedDispatcher(NamedTuple, DispatcherInterface):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """
    manager: ManagerInterface
    LOW_SOC_TRESHOLD: float = 0.2

    @classmethod
    def build(cls,
              manager: ManagerInterface,
              low_soc_threshold: float = 0.2) -> ManagedDispatcher:

        return ManagedDispatcher(
            manager=manager,
            LOW_SOC_TRESHOLD=low_soc_threshold
        )

    @staticmethod
    def _gen_report(instruction: Instruction, sim_time: SimTime) -> dict:
        i_dict = instruction._asdict()
        i_dict['sim_time'] = sim_time
        i_dict['report_type'] = "dispatcher"
        i_dict['instruction_type'] = instruction.__class__.__name__

        return i_dict

    def generate_instructions(self,
                              simulation_state: 'SimulationState',
                              ) -> Tuple[DispatcherInterface, Dict[VehicleId, Instruction], Tuple[Report, ...]]:

        instruction_map = {}

        updated_manager, fleet_targets, reports = self.manager.generate_fleet_targets(simulation_state)

        for fleet_target in fleet_targets:
            fleet_target_instructions = fleet_target.apply_target(simulation_state)
            for v_id, instruction in fleet_target_instructions.items():
                instruction_map[v_id] = instruction

        # find requests that need a vehicle. Sorted by price high to low.
        # these instructions override fleet target instructions
        already_dispatched = []

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            is_valid_state = isinstance(vehicle.vehicle_state, Idle) or \
                             isinstance(vehicle.vehicle_state, Repositioning)

            return bool(vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD
                        and is_valid_state and vehicle.id not in already_dispatched)

        unassigned_requests = sorted(
            [r for r in simulation_state.requests.values() if not r.dispatched_vehicle],
            key=lambda r: r.value,
            reverse=True,
        )
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

                already_dispatched.append(nearest_vehicle.id)

                report = self._gen_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instruction_map[nearest_vehicle.id] = instruction

        # find vehicles that fall below the minimum threshold and charge them.
        # these instructions override dispatch instructions

        low_soc_vehicles = [v for v in simulation_state.vehicles.values()
                            if v.energy_source.soc <= self.LOW_SOC_TRESHOLD
                            and v.vehicle_state.__class__.__name__ != 'DispatchStation']

        for veh in low_soc_vehicles:
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_search=simulation_state.s_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   max_distance_km=100,
                                                   is_valid=lambda s: s.has_available_charger(Charger.DCFC))
            if nearest_station:
                instruction = DispatchStationInstruction(
                    vehicle_id=veh.id,
                    station_id=nearest_station.id,
                    charger=Charger.DCFC,
                )

                report = self._gen_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instruction_map[veh.id] = instruction
            else:
                # user set the max search radius too low (should really be computed by
                # HIVE based on the RoadNetwork at initialization anyway)
                # also possible: no charging stations available. implement a queueing solution
                # for agents who could wait to charge
                print("warning, no open stations found")
                continue

        # charge any remaining vehicles sitting at base.
        # these instructions do not override any of the previous instructions
        def _should_base_charge(vehicle: Vehicle) -> bool:
            return bool(isinstance(vehicle.vehicle_state, ChargingBase)
                        and not vehicle.energy_source.is_at_ideal_energy_limit())

        base_charge_vehicles = [v for v in simulation_state.vehicles.values() if
                                v.id not in instruction_map and _should_base_charge(v)]

        for v in base_charge_vehicles:
            base_id = simulation_state.b_locations[v.geoid]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = ChargeBaseInstruction(
                    vehicle_id=v.id,
                    base_id=base.id,
                    charger=Charger.LEVEL_2,
                )

                report = self._gen_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instruction_map[v.id] = instruction

        return self._replace(manager=updated_manager), instruction_map, reports
