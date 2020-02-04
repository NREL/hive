from __future__ import annotations

import functools as ft
import json
from typing import Tuple, Optional, NamedTuple

from hive.runner.environment import Environment
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.model.instruction.instruction_interface import Instruction
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import SimTime


class StepSimulation(NamedTuple, SimulationUpdateFunction):
    dispatcher: DispatcherInterface

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment,
    ) -> Tuple[SimulationUpdateResult, Optional[StepSimulation]]:
        """
        cancels requests whose cancel time has been exceeded

        :param simulation_state: state to modify
        :param env:
        :return: state without cancelled requests, along with this update function
        """
        updated_dispatcher, instructions = self.dispatcher.generate_instructions(simulation_state)
        sim_with_instructions = self._apply_instructions(simulation_state, instructions)
        sim_next_time_step = sim_with_instructions.step_simulation(env)
        reports = tuple(self._as_json(i, simulation_state.sim_time) for i in instructions)

        return SimulationUpdateResult(sim_next_time_step, reports=reports), self._replace(dispatcher=updated_dispatcher)

    def _apply_instructions(
            self,
            simulation_state: SimulationState,
            instructions: Tuple[Instruction, ...]) -> SimulationState:
        """
        applies all the instructions to the simulation state, ignoring the ones that fail

        :param simulation_state: the sim state
        :param instructions: dispatcher instructions
        :return: the sim state with vehicle intentions updated
        """
        return ft.reduce(
            self._add_instruction,
            instructions,
            simulation_state
        )

    def _add_instruction(self, simulation_state: SimulationState, instruction: Instruction) -> SimulationState:
        """
        inner loop for apply_instructions method

        :param simulation_state: the intermediate sim state
        :param instruction: the ith instruction
        :return: sim state with the ith instruction added, unless it's bogus
        """
        updated_sim = instruction.apply_instruction(simulation_state)
        if updated_sim is None:
            return simulation_state
        return updated_sim

    def _as_json(self, instruction: Instruction, sim_time: SimTime) -> str:
        i_dict = instruction._asdict()
        i_dict['sim_time'] = sim_time
        i_dict['report'] = "instruction"
        i_dict['instruction_type'] = instruction.__class__.__name__
        return json.dumps(i_dict, default=str)


