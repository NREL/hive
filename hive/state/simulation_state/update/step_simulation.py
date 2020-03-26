from __future__ import annotations

import functools as ft
from typing import Tuple, Dict, Optional, NamedTuple, TYPE_CHECKING

from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.model.instruction.instruction_interface import Instruction
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.runner.environment import Environment


def step_simulation(simulation_state: SimulationState, env: Environment) -> SimulationState:
    def _step_vehicle(s: SimulationState, vid: VehicleId) -> SimulationState:
        vehicle = s.vehicles.get(vid)
        if vehicle is None:
            env.reporter.sim_report({'error': f"vehicle {vid} not found"})
            return simulation_state
        else:
            error, updated_sim = vehicle.vehicle_state.update(s, env)
            if error:
                env.reporter.sim_report({'error': error})
                return simulation_state
            else:
                return updated_sim

    next_state = ft.reduce(
        _step_vehicle,
        tuple(simulation_state.vehicles.keys()),
        simulation_state,
    )

    return next_state.tick()


def apply_instructions(simulation_state: SimulationState,
                       env: Environment,
                       instructions: Dict[VehicleId, Instruction]) -> SimulationState:
    def _add_instruction(
            s: SimulationState,
            instruction: Instruction,
    ) -> SimulationState:
        update_error, updated_sim = instruction.apply_instruction(s, env)
        if update_error:
            env.reporter.sim_report({'error': update_error})
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
        updated_dispatcher, instructions, reports = self.dispatcher.generate_instructions(simulation_state)
        sim_with_instructions = apply_instructions(simulation_state, env, instructions)
        sim_next_time_step = step_simulation(
            simulation_state=sim_with_instructions,
            env=env,
        )

        return SimulationUpdateResult(sim_next_time_step, reports=reports), self._replace(dispatcher=updated_dispatcher)


