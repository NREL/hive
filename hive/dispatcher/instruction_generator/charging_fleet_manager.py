from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.util.units import Ratio, Kilometers

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import instruct_vehicles_dispatch_to_station, sit_idle
from hive.state.vehicle_state import Idle, Repositioning, ChargingStation

log = logging.getLogger(__name__)


class ChargingFleetManager(NamedTuple, InstructionGenerator):
    """
    A manager that instructs vehicles to charge if they fall below an SOC threshold.
    """
    low_soc_threshold: Ratio
    ideal_fastcharge_soc_limit: Ratio
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

        # find vehicles that fall below the minimum threshold and charge them.

        def charge_candidate(v: Vehicle) -> bool:
            proper_state = isinstance(v.vehicle_state, Idle) or isinstance(v.vehicle_state, Repositioning)
            return v.energy_source.soc <= self.low_soc_threshold and proper_state

        def stop_charge_candidate(v: Vehicle) -> bool:
            proper_state = isinstance(v.vehicle_state, ChargingStation)
            return v.energy_source.soc >= self.ideal_fastcharge_soc_limit and proper_state

        low_soc_vehicles = simulation_state.get_vehicles(filter_function=charge_candidate)
        high_soc_vehicles = simulation_state.get_vehicles(filter_function=stop_charge_candidate)

        charge_instructions = instruct_vehicles_dispatch_to_station(n=len(low_soc_vehicles),
                                                                    max_search_radius_km=self.max_search_radius_km,
                                                                    vehicles=low_soc_vehicles,
                                                                    simulation_state=simulation_state)
        stop_charge_instructions = sit_idle(len(high_soc_vehicles), high_soc_vehicles)

        instructions = charge_instructions + stop_charge_instructions

        return self, instructions, ()
