from __future__ import annotations

from typing import Tuple, NamedTuple, TYPE_CHECKING

import immutables
import logging

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction, InstructionMap
    from hive.model.vehicle.vehicle import Vehicle
    from hive.util.typealiases import Report, SimTime

from hive.dispatcher.instructors.instructor_interface import InstructorInterface
from hive.dispatcher.instruction.instructions import (
    DispatchStationInstruction,
    ChargeBaseInstruction
)
from hive.state.vehicle_state import DispatchStation, ChargingBase
from hive.model.energy.charger import Charger
from hive.util.helpers import H3Ops, DictOps

log = logging.getLogger(__name__)


class BasicCharging(NamedTuple, InstructorInterface):
    """
    A instructors algorithm that assigns vehicles greedily to most expensive request.
    """
    LOW_SOC_TRESHOLD = 0.2

    @staticmethod
    def _gen_report(instruction: Instruction, sim_time: SimTime) -> Report:
        i_dict = instruction._asdict()
        i_dict['sim_time'] = sim_time
        i_dict['report_type'] = "dispatcher"
        i_dict['instruction_type'] = instruction.__class__.__name__

        return i_dict

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            previous_instructions: InstructionMap,
    ) -> Tuple[BasicCharging, InstructionMap, Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state
        :param previous_instructions: instructions from previous modules

        :return: the updated Manager along with fleet targets and reports
        """

        new_instructions = immutables.Map()
        reports = ()

        # find vehicles that fall below the minimum threshold and charge them.
        # these instructions override dispatch instructions

        low_soc_vehicles = [v for v in simulation_state.vehicles.values()
                            if v.energy_source.soc <= self.LOW_SOC_TRESHOLD
                            and not isinstance(v.vehicle_state, DispatchStation)]

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

                new_instructions = DictOps.add_to_dict(new_instructions, veh.id, instruction)
            else:
                # user set the max search radius too low (should really be computed by
                # HIVE based on the RoadNetwork at initialization anyway)
                # also possible: no charging stations available. implement a queueing solution
                # for agents who could wait to charge
                log.warning(f"no open stations found at time {simulation_state.sim_time} for vehicle {veh.id}")
                continue

        # charge any remaining vehicles sitting at base.
        # these instructions do not override any of the previous instructions
        def _should_base_charge(vehicle: Vehicle) -> bool:
            return bool(isinstance(vehicle.vehicle_state, ChargingBase)
                        and not vehicle.energy_source.is_at_ideal_energy_limit())

        base_charge_vehicles = [v for v in simulation_state.vehicles.values() if
                                v.id not in previous_instructions and _should_base_charge(v)]

        for veh in base_charge_vehicles:
            base_id = simulation_state.b_locations[veh.geoid]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = ChargeBaseInstruction(
                    vehicle_id=veh.id,
                    base_id=base.id,
                    charger=Charger.LEVEL_2,
                )

                report = self._gen_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                new_instructions = DictOps.add_to_dict(new_instructions, veh.id, instruction)

        return self, DictOps.merge_dicts(previous_instructions, new_instructions), reports
