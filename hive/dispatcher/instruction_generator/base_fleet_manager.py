from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import instruct_vehicles_at_base_to_charge
from hive.model.energy.energytype import EnergyType
from hive.state.vehicle_state.reserve_base import ReserveBase

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.vehicle.vehicle import Vehicle
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.config.dispatcher_config import DispatcherConfig

log = logging.getLogger(__name__)


class BaseFleetManager(NamedTuple, InstructionGenerator):
    """
    A manager that instructs vehicles on how to behave at the base.

    NOTE: This manager only evaluates electric vehicles and is not designed to handle other vehicle types.
    """
    config: DispatcherConfig

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[BaseFleetManager, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param environment:
        :param simulation_state: The current simulation state

        :return: the updated BaseFleetManager along with instructions
        """

        def _sort_key(v: Vehicle) -> float:
            if EnergyType.ELECTRIC in v.energy.keys():
                return v.energy[EnergyType.ELECTRIC]
            else:
                return 999999

        def _filter_function(v: Vehicle) -> bool:
            right_state = isinstance(v.vehicle_state, ReserveBase)
            right_energy = EnergyType.ELECTRIC in v.energy.keys()
            return right_state and right_energy

        reserve_vehicles = simulation_state.get_vehicles(
            sort=True,
            sort_key=_sort_key,
            filter_function=_filter_function,
        )

        charge_instructions = instruct_vehicles_at_base_to_charge(
            reserve_vehicles,
            simulation_state,
            environment,
        )

        return self, charge_instructions
