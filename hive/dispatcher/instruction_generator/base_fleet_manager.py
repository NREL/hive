from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING, Optional

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import charge_at_base
from hive.state.vehicle_state import (
    ReserveBase,
)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
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

        reserve_vehicles = simulation_state.get_vehicles(
            sort=True,
            sort_key=lambda v: v.energy_source.soc,
            filter_function=lambda v: isinstance(v.vehicle_state, ReserveBase),
        )

        if self.base_vehicles_charging_limit:
            target = self.base_vehicles_charging_limit
        else:
            target = len(reserve_vehicles)

        charge_instructions = charge_at_base(target, reserve_vehicles, simulation_state)

        return self, charge_instructions, ()
