from __future__ import annotations

import functools as ft
from typing import Tuple, NamedTuple, TYPE_CHECKING

import immutables

from hive.util.helpers import DictOps

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
    from hive.util.typealiases import Report


class InstuctionGenerationResult(NamedTuple):
    instruction_map: immutables.Map = immutables.Map()
    reports: Tuple[Report, ...] = ()
    updated_instruction_generators: Tuple[InstructionGenerator, ...] = ()

    def apply_instruction_generator(self,
                                    instruction_generator: InstructionGenerator,
                                    simulation_state: 'SimulationState') -> InstuctionGenerationResult:
        """
        generates instructions from one InstructionGenerator and updates the result accumulator
        :param instruction_generator: an InstructionGenerator to apply to the SimulationState
        :param simulation_state: the current simulation state
        :return: the updated accumulator
        """
        updated_gen, new_instructions, new_reports = instruction_generator.generate_instructions(simulation_state)

        updated_instruction_map = ft.reduce(
            lambda acc, i: DictOps.add_to_dict(acc, i.vehicle_id, i),
            new_instructions,
            self.instruction_map
        )

        return self._replace(
            instruction_map=updated_instruction_map,
            reports=self.reports + new_reports,
            updated_instruction_generators=self.updated_instruction_generators + (updated_gen,)
        )


def generate_instructions(instruction_generators: Tuple[InstructionGenerator, ...],
                          simulation_state: 'SimulationState',
                          ) -> InstuctionGenerationResult:
    """
    applies a set of InstructionGenerators to the SimulationState. order of generators is preserved
    and has an overwrite behavior with respect to generated Instructions in the instruction_map

    :param instruction_generators:
    :param simulation_state:
    :return: the instructions generated for this time step, which has 0 or 1 instruction per vehicle
    """

    result = ft.reduce(
        lambda acc, gen: acc.apply_instruction_generator(gen, simulation_state),
        instruction_generators,
        InstuctionGenerationResult()
    )

    return result
