from __future__ import annotations

import functools as ft
import logging
from typing import Tuple, Optional, TYPE_CHECKING, Callable, NamedTuple

import immutables

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instruction_result import InstructionResult
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.state.entity_state import entity_state_ops
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util import TupleOps
from hive.util.typealiases import VehicleId, Report

if TYPE_CHECKING:
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


def perform_vehicle_state_updates(simulation_state: SimulationState, env: Environment) -> SimulationState:
    """
    helper function for StepSimulation which applies a vehicle state update to each vehicle
    :param simulation_state: the simulation state to update
    :param env: the simulation environment
    :return: the sim after all vehicle update functions have been called
    """

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
        simulation_state.vehicle_iterator,
        simulation_state,
    )

    return simulation_state_ops.tick(next_state)


def apply_instructions(sim: SimulationState,
                       env: Environment,
                       instructions: immutables.Map[VehicleId, Instruction]) -> SimulationState:
    """
    this helper function takes a map with one instruction per agent at most, and attempts to apply each
    instruction to the simulation, managing the instruction's externalities, and managing failure.

    :param sim: the current simulation state
    :param env: the sim environment
    :param instructions: all instructions to add at this time step
    :return: the simulation state modified by all successful Instructions
    """

    # construct the vehicle state transitions
    run_in_parallel = False  # env.config.system.local_parallelism > 1

    if run_in_parallel:
        # run in parallel
        # todo: inject some means for parallel execution of the apply instruction operation
        #   requires shared memory access to SimulationState and Environment,
        #   and a serialization codec to ship Instructions and Instruction.apply_instruction remotely
        result = ((NotImplementedError, None),)
    else:
        # run in a synchronous loop
        result = ft.reduce(lambda acc, i: acc + (i.apply_instruction(sim, env),), instructions.values(), ())

    has_errors, no_errors = TupleOps.partition(lambda t: t[0] is not None, result)
    valid_instruction_results = map(lambda t: t[1], no_errors)
    # report any errors from applying instructions
    if len(has_errors) > 0:
        # at least one failed
        for err, _ in has_errors:
            log.error(err)

    # update the simulation with each vehicle state transition in sequence
    def _add_instruction(
            s: SimulationState,
            i: InstructionResult,
    ) -> SimulationState:
        update_error, updated_sim = entity_state_ops.transition_previous_to_next(s, env, i.prev_state, i.next_state)
        if update_error:
            log.error(update_error)
            return s
        elif updated_sim is None:
            return s
        else:
            return updated_sim

    return ft.reduce(
        _add_instruction,
        valid_instruction_results,
        sim
    )


class UserProvidedUpdateAccumulator(NamedTuple):
    updated_fns: Tuple[InstructionGenerator, ...] = ()
    reports: Tuple[Report, ...] = ()

    def apply_updated_instruction_generator(self, i: InstructionGenerator):
        return self._replace(updated_fns=self.updated_fns + (i,))

    def apply_report(self, r: Report):
        return self._replace(reports=self.reports + (r,))

    def has_errors(self) -> bool:
        return len(self.reports) > 0


def instruction_generator_update_fn(
        fn: Callable[[InstructionGenerator, SimulationState], Optional[InstructionGenerator]],
        sim: SimulationState
) -> Callable[[UserProvidedUpdateAccumulator, InstructionGenerator], UserProvidedUpdateAccumulator]:
    """
    applies a user-provided function designed to inject an external update to InstructionGenerators
    :param fn: the function which applies an update or returns None for no update
    :param sim: the simulation state, which will not be modified but available to the update function
    :return: the updated list of InstructionGenerators
    """

    def _inner(acc: UserProvidedUpdateAccumulator,
               i: InstructionGenerator
               ) -> UserProvidedUpdateAccumulator:
        try:
            result = fn(i, sim)
            if not result:
                return acc.apply_updated_instruction_generator(i)
            else:
                return acc.apply_updated_instruction_generator(result)
        except Exception as e:
            return acc.apply_report({'report_type': 'error', 'message': repr(e)})

    return _inner
