from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING, Optional

from hive.dispatcher.instruction.instruction_interface import instruction_to_report
from hive.dispatcher.instruction.instructions import (
    ChargeBaseInstruction,
    ReserveBaseInstruction,
)
from hive.dispatcher.managers.manager_interface import ManagerInterface
from hive.external.demo_base_target.temp_base_target import BaseTarget
from hive.model.energy.charger import Charger
from hive.state.vehicle_state import (
    ReserveBase,
    ChargingBase,
)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

log = logging.getLogger(__name__)


class BaseManagement(NamedTuple, ManagerInterface):
    """
    A manager that instructs vehicles on how to behave at the base
    """
    base_vehicles_charging_limit: Optional[int]
    base_target: BaseTarget = BaseTarget()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[BaseManagement, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """

        instructions = ()
        reports = ()

        base_charge_vehicles = [v for v in simulation_state.vehicles.values()
                                if isinstance(v.vehicle_state, ChargingBase)]
        reserve_vehicles = [v for v in simulation_state.vehicles.values()
                            if isinstance(v.vehicle_state, ReserveBase)]

        n_charging = len(base_charge_vehicles)

        target = self.base_target.get_target(simulation_state.sim_time)

        if target > n_charging:
            # we want more vehicles charging
            # assign as many of these vehicles to charge as possible, sorted by SOC ascending
            reserve_vehicles.sort(key=lambda v: v.energy_source.soc)
            diff = target - n_charging
            for veh in reserve_vehicles:
                if len(instructions) >= diff:
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
        elif target < n_charging:
            # we have too many vehicles charging
            # instruct the extra vehicles to reserve, sorted by SOC descending
            base_charge_vehicles.sort(key=lambda v: v.energy_source.soc, reverse=True)
            diff = n_charging - target
            for veh in base_charge_vehicles:
                if len(instructions) >= diff:
                    break

                base_id = simulation_state.b_locations[veh.geoid]
                instruction = ReserveBaseInstruction(
                    vehicle_id=veh.id,
                    base_id=base_id,
                )

                report = instruction_to_report(instruction, simulation_state.sim_time)
                reports = reports + (report,)

                instructions = instructions + (instruction,)

        return self, instructions, reports
