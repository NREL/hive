from __future__ import annotations

import functools as ft
import logging
from typing import Tuple, Dict, Optional, NamedTuple, TYPE_CHECKING

import immutables

from hive.dispatcher.instruction.instruction_interface import Instruction
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import generate_instructions
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


def step_simulation(simulation_state: SimulationState, env: Environment) -> SimulationState:
    def _step_vehicle(s: SimulationState, vid: VehicleId) -> SimulationState:
        vehicle = s.vehicles.get(vid)
        if vehicle is None:
            env.reporter.sim_report({'error': f"vehicle {vid} not found"})
            return simulation_state
        else:
            error, updated_sim = vehicle.vehicle_state.update(s, env)
            if error:
                log.error(error)
                return simulation_state
            elif not updated_sim:
                return simulation_state
            else:
                return updated_sim

    next_state = ft.reduce(
        _step_vehicle,
        tuple(simulation_state.vehicles.keys()),
        simulation_state,
    )

    return simulation_state_ops.tick(next_state)


def apply_instructions(simulation_state: SimulationState,
                       env: Environment,
                       instructions: immutables.Map[VehicleId, Instruction]) -> SimulationState:
    def _add_instruction(
            s: SimulationState,
            instruction: Instruction,
    ) -> SimulationState:
        update_error, updated_sim = instruction.apply_instruction(s, env)
        if update_error:
            log.error(update_error)
            return s
        elif updated_sim is None:
            return s
        else:
            return updated_sim

    return ft.reduce(
        _add_instruction,
        instructions.values(),
        simulation_state
    )


class StepSimulation(NamedTuple, SimulationUpdateFunction):
    instruction_generators: Tuple[InstructionGenerator, ...]

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment,
    ) -> Tuple[SimulationUpdateResult, Optional[StepSimulation]]:
        """
        generates all instructions for this time step and then attempts to apply them to the SimulationState
        upon completion, returns the modified simulation state along with any reports and additionally, returns
        an updated version of the StepSimulation (in the case of any modifications to the InstructionGenerators)

        :param simulation_state: state to modify
        :param env: the sim environment
        :return: updated simulation state, with reports, along with the (optionally) updated StepSimulation
        """
        instr_result = generate_instructions(self.instruction_generators, simulation_state)
        sim_with_instructions = apply_instructions(simulation_state, env, instr_result.instruction_map)
        sim_next_time_step = step_simulation(simulation_state=sim_with_instructions, env=env)
        update_result = SimulationUpdateResult(simulation_state=sim_next_time_step, reports=instr_result.reports)
        updated_step_simulation = self._replace(instruction_generators=instr_result.updated_instruction_generators)

        return update_result, updated_step_simulation


