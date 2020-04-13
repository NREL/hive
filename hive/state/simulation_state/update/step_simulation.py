from __future__ import annotations

import functools as ft
import logging
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING, Callable

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import generate_instructions
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.simulation_update_result import SimulationUpdateResult
from hive.state.simulation_state.update.step_simulation_ops import (
    perform_vehicle_state_updates,
    apply_instructions,
    instruction_generator_update_fn,
    UserProvidedUpdateAccumulator)

if TYPE_CHECKING:
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


class StepSimulation(NamedTuple, SimulationUpdateFunction):
    instruction_generators: Tuple[InstructionGenerator, ...]
    instruction_generator_update_fn: Callable[
        [InstructionGenerator, SimulationState], Optional[InstructionGenerator]] = lambda a, b: None

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment,
    ) -> Tuple[SimulationUpdateResult, Optional[StepSimulation]]:
        """
        generates all instructions for this time step and then attempts to apply them to the SimulationState
        upon completion, returns the modified simulation state along with any reports and additionally, returns
        an updated version of the StepSimulation (in the case of any modifications to the InstructionGenerators)

        before beginning, it first calls a provided update function on the set of InstructionGenerators for any
        control models injected by the user

        :param simulation_state: state to modify
        :param env: the sim environment
        :return: updated simulation state, with reports, along with the (optionally) updated StepSimulation
        """
        # allow the user to inject changes to the InstructionGenerators
        user_update_result = ft.reduce(
            instruction_generator_update_fn(self.instruction_generator_update_fn, simulation_state),
            self.instruction_generators,
            UserProvidedUpdateAccumulator()
        )

        if user_update_result.has_errors():
            # stop here, passing back the error(s) and the result of the user update
            updated_step_simulation = self._replace(instruction_generators=user_update_result.updated_fns)
            return SimulationUpdateResult(simulation_state, user_update_result.reports), updated_step_simulation
        else:

            # generate Instructions, which may also have the side effect of modifying the InstructionGenerators
            instr_result = generate_instructions(user_update_result.updated_fns, simulation_state)
            sim_with_instructions = apply_instructions(simulation_state, env, instr_result.instruction_map)
            sim_next_time_step = perform_vehicle_state_updates(simulation_state=sim_with_instructions, env=env)
            update_result = SimulationUpdateResult(simulation_state=sim_next_time_step, reports=instr_result.reports)
            updated_step_simulation = self._replace(instruction_generators=instr_result.updated_instruction_generators)

            return update_result, updated_step_simulation
