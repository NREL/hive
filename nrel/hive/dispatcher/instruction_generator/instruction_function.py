from __future__ import annotations

from typing import Tuple, Callable, TYPE_CHECKING, Union

from nrel.hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.runner.environment import Environment
from nrel.hive.dispatcher.instruction.instruction import Instruction


InstructionFunction = Callable[[SimulationState, Environment], Tuple[Instruction, ...]]


class AnonGenerator(InstructionGenerator):
    """
    A class that wraps an instruction function as an instruction generator
    """

    def __init__(self, instruction_function: InstructionFunction):
        self.instruction_function = instruction_function

    @property
    def name(self) -> str:
        # return the name of the function
        return self.instruction_function.__name__

    def generate_instructions(
        self,
        simulation_state: SimulationState,
        environment: Environment,
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...]]:
        return self, self.instruction_function(simulation_state, environment)


def instruction_generator_from_function(
    ig_or_if: Union[InstructionFunction, InstructionGenerator],
) -> InstructionGenerator:
    """
    A helper function to wrap an instruction function as an instruction generator
    """
    # check if the input is a callable
    if callable(ig_or_if):
        return AnonGenerator(ig_or_if)

    # otherwise, assume it is already an instruction generator
    return ig_or_if
