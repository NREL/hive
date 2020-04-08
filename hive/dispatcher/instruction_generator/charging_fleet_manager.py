from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.util.units import Ratio, Kilometers

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction.instruction_interface import instruction_to_report
from hive.dispatcher.instruction.instructions import (
    DispatchStationInstruction
)
from hive.state.vehicle_state import DispatchStation
from hive.model.energy.charger import Charger
from hive.util.helpers import H3Ops

log = logging.getLogger(__name__)


class ChargingFleetManager(NamedTuple, InstructionGenerator):
    """
    A manager that instructs vehicles to charge if they fall below an SOC threshold.
    """
    low_soc_threshold: Ratio
    max_search_radius_km: Kilometers

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[ChargingFleetManager, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """

        instructions = ()
        reports = ()

        # find vehicles that fall below the minimum threshold and charge them.
        low_soc_vehicles = [v for v in simulation_state.vehicles.values()
                            if v.energy_source.soc <= self.low_soc_threshold
                            and not isinstance(v.vehicle_state, DispatchStation)]

        for veh in low_soc_vehicles:
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_search=simulation_state.s_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   max_distance_km=self.max_search_radius_km,
                                                   is_valid=lambda s: s.has_available_charger(Charger.DCFC))
            if nearest_station:
                instruction = DispatchStationInstruction(
                    vehicle_id=veh.id,
                    station_id=nearest_station.id,
                    charger=Charger.DCFC,
                )

                report = instruction_to_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instructions = instructions + (instruction,)
            else:
                # user set the max search radius too low (should really be computed by
                # HIVE based on the RoadNetwork at initialization anyway)
                # also possible: no charging stations available. implement a queueing solution
                # for agents who could wait to charge
                log.info(f"no open stations found at time {simulation_state.sim_time} for vehicle {veh.id}")
                continue

        return self, instructions, reports
