from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING, Optional

from hive.dispatcher.instruction.instruction_interface import instruction_to_report
from hive.dispatcher.instruction.instructions import (
    ChargeBaseInstruction,
    ReserveBase)
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.model.energy.charger import Charger

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.model.vehicle.vehicle import Vehicle
    from hive.util.typealiases import Report

log = logging.getLogger(__name__)


class BaseFleetManager(NamedTuple, InstructionGenerator):
    """
    A manager that instructs vehicles on how to behave at the base
    """
    base_vehicles_charging_limit: Optional[int]

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[BaseFleetManager, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """

        instructions = ()
        reports = ()

        def _should_base_charge(vehicle: Vehicle) -> bool:
            return bool(isinstance(vehicle.vehicle_state, ReserveBase) and not
                        vehicle.energy_source.is_at_ideal_energy_limit())

        # find vehicles that should charge and sort them by SoC, ascending
        base_charge_vehicles = [v for v in simulation_state.vehicles.values() if _should_base_charge(v)]
        base_charge_vehicles.sort(key=lambda v: v.energy_source.soc)

        # assign as many of these vehicles to charge as possible
        for veh in base_charge_vehicles:
            if self.base_vehicles_charging_limit and len(instructions) >= self.base_vehicles_charging_limit:
                break
            base_id = simulation_state.b_locations[veh.geoid]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = ChargeBaseInstruction(
                    vehicle_id=veh.id,
                    base_id=base.id,
                    charger=Charger.LEVEL_2,
                )

                report = instruction_to_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instructions = instructions + (instruction,)

        return self, instructions, reports
