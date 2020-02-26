from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, NamedTuple

from hive.runner.environment import Environment
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.model.instruction.instruction_interface import Instruction
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import SimTime, VehicleId


def step_simulation(simulation_state: SimulationState, env: Environment) -> SimulationState:
    def _step_vehicle(s: SimulationState, vid: VehicleId) -> SimulationState:
        updated_sim = s.step_vehicle(vid, env)
        if updated_sim is None:
            return simulation_state
        return updated_sim

    next_state = ft.reduce(
        _step_vehicle,
        tuple(simulation_state.vehicles.keys()),
        simulation_state,
    )

    return next_state.tick()


def apply_instructions(simulation_state: SimulationState, instructions: Tuple[Instruction, ...]) -> SimulationState:
    def _add_instruction(
            s: SimulationState,
            instruction: Instruction,
    ) -> SimulationState:
        updated_sim = instruction.apply_instruction(s)
        if updated_sim is None:
            return simulation_state
        return updated_sim

    return ft.reduce(
        _add_instruction,
        instructions,
        simulation_state
    )


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
        sim_with_instructions = apply_instructions(simulation_state, instructions)
        sim_next_time_step = step_simulation(
            simulation_state=sim_with_instructions,
            env=env,
        )
        reports = tuple(self._gen_report(i, simulation_state.sim_time) for i in instructions)

        return SimulationUpdateResult(sim_next_time_step, reports=reports), self._replace(dispatcher=updated_dispatcher)

    def _gen_report(self, instruction: Instruction, sim_time: SimTime) -> dict:
        i_dict = instruction._asdict()
        i_dict['sim_time'] = sim_time
        i_dict['report_type'] = "dispatcher"
        i_dict['instruction_type'] = instruction.__class__.__name__
        return i_dict
