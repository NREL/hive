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
from hive.dispatcher.instruction_generator.instruction_generator_ops import charge_at_station
from hive.state.vehicle_state import Idle, Repositioning

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

        # find vehicles that fall below the minimum threshold and charge them.

        def charge_candidate(v: Vehicle) -> bool:
            proper_state = isinstance(v.vehicle_state, Idle) or isinstance(v.vehicle_state, Repositioning)
            return v.energy_source.soc <= self.low_soc_threshold and proper_state

        low_soc_vehicles = simulation_state.get_vehicles(filter_function=charge_candidate)

        charge_instructions = charge_at_station(len(low_soc_vehicles), low_soc_vehicles, simulation_state)

        return self, charge_instructions, ()
