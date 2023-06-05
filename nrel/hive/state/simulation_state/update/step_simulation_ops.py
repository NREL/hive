from __future__ import annotations

import functools as ft
import logging
from dataclasses import asdict
from typing import List, Tuple, Optional, TYPE_CHECKING, Callable, NamedTuple

from nrel.hive.dispatcher.instruction.instruction import Instruction
from nrel.hive.dispatcher.instruction.instruction_result import InstructionResult
from nrel.hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.reporting.report_type import ReportType
from nrel.hive.reporting.reporter import Report
from nrel.hive.state.entity_state import entity_state_ops
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.state.vehicle_state.charge_queueing import ChargeQueueing
from nrel.hive.util import TupleOps

if TYPE_CHECKING:
    from nrel.hive.runner.environment import Environment
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.model.sim_time import SimTime

log = logging.getLogger(__name__)


def _instruction_to_report(i: Instruction, sim_time: SimTime) -> Report:
    i_dict = asdict(i)
    i_dict["sim_time"] = sim_time
    i_dict["instruction_type"] = i.__class__.__name__

    return Report(ReportType.INSTRUCTION, i_dict)


def log_instructions(instructions: Tuple[Instruction, ...], env: Environment, sim_time: SimTime):
    for i in instructions:
        env.reporter.file_report(_instruction_to_report(i, sim_time))


def step_vehicle(s: SimulationState, env: Environment, vehicle: Vehicle) -> SimulationState:
    error, updated_sim = vehicle.vehicle_state.update(s, env)
    if error:
        log.error(error)
        return s
    elif not updated_sim:
        return s
    else:
        return updated_sim


def perform_driver_state_updates(
    simulation_state: SimulationState, env: Environment
) -> SimulationState:
    """
    helper function for StepSimulation which runs the update function for all driver states

    :param simulation_state: the simulation state to update
    :param env: the simulation environment
    :return: the sim after all vehicle update functions have been called
    """

    def _step_drivers(s: SimulationState, vehicle: Vehicle) -> SimulationState:
        driver_state = vehicle.driver_state
        error, updated_sim = driver_state.update(s, env)
        if error:
            log.error(error)
            return simulation_state
        elif not updated_sim:
            return simulation_state
        else:
            return updated_sim

    next_state = ft.reduce(_step_drivers, simulation_state.get_vehicles(), simulation_state)
    return next_state


def perform_vehicle_state_updates(
    simulation_state: SimulationState, env: Environment
) -> SimulationState:
    """
    helper function for StepSimulation which applies a vehicle state update to each vehicle

    :param simulation_state: the simulation state to update
    :param env: the simulation environment
    :return: the sim after all vehicle update functions have been called
    """

    def _sort_by_vehicle_state(vs: Tuple[Vehicle, ...]) -> Tuple[Vehicle, ...]:
        """
        a one-pass partitioning to place ChargeQueueing agents after their non-ChargeQueueing friends
        and to sort the charge queueing agents by their enqueue_time

        if we need additional sort criteria for future VehicleStates we may need to
        instead call sim.get_vehicles with a sort_key function in place of this shortcut


        :param vs: the vehicles
        :return: the vehicles with all ChargeQueueing vehicles at the tail
        """
        charge_queueing_vehicles, other_vehicles = TupleOps.partition(
            lambda v: isinstance(v.vehicle_state, ChargeQueueing), vs
        )

        # sort queueing vehicles by enqueue time followed by id as a
        # deterministic tie-breaker via their VehicleId
        sorted_charge_queueing_vehicles = tuple(
            sorted(
                charge_queueing_vehicles,
                key=lambda v: (v.vehicle_state.enqueue_time, v.id)
                if isinstance(v.vehicle_state, ChargeQueueing)
                else (0, v.id),
            )
        )
        sorted_other_vehicles = tuple(sorted(other_vehicles, key=lambda v: v.id))
        return sorted_other_vehicles + sorted_charge_queueing_vehicles

    # why sort here? see _sort_by_vehicle_state (above) for an explanation
    # this code doesn't use built-in sorting iterator methods because of the
    # initial partitioning step required.
    vehicles = _sort_by_vehicle_state(tuple(simulation_state.vehicles.values()))

    for veh in vehicles:
        simulation_state = step_vehicle(simulation_state, env, veh)

    return simulation_state


InstructionApplicationResult = Tuple[Optional[Exception], Optional[InstructionResult]]


def apply_instructions(
    sim: SimulationState, env: Environment, instructions: Tuple[Instruction, ...]
) -> SimulationState:
    """
    this helper function takes a map with one instruction per agent at most, and attempts to apply each
    instruction to the simulation, managing the instruction's externalities, and managing failure.

    :param sim: the current simulation state
    :param env: the sim environment
    :param instructions: all instructions to add at this time step
    :return: the simulation state modified by all successful Instructions
    """
    # construct the vehicle state transitions

    results: List[InstructionResult] = []
    for instruction in instructions:
        err, instruction_result = instruction.apply_instruction(sim, env)
        if err is not None:
            log.error(err)
            continue
        if instruction_result is None:
            log.error("this should not be none if error is not none")
            continue

        updated_instructions = sim.applied_instructions.update(
            {instruction.vehicle_id: instruction}
        )
        sim = sim._replace(applied_instructions=updated_instructions)

        results.append(instruction_result)

    for instruction_result in results:
        result = entity_state_ops.transition_previous_to_next(
            sim, env, instruction_result.prev_state, instruction_result.next_state
        )
        update_error, updated_sim = result
        if update_error:
            log.error(update_error)
            continue
        elif updated_sim is None:
            continue
        else:
            sim = updated_sim

    return sim


class UserProvidedUpdateAccumulator(NamedTuple):
    updated_fns: Tuple[InstructionGenerator, ...] = ()

    def apply_updated_instruction_generator(self, i: InstructionGenerator):
        return self._replace(updated_fns=self.updated_fns + (i,))


def instruction_generator_update_fn(
    fn: Callable[[InstructionGenerator, SimulationState], Optional[InstructionGenerator]],
    sim: SimulationState,
) -> Callable[
    [UserProvidedUpdateAccumulator, InstructionGenerator],
    UserProvidedUpdateAccumulator,
]:
    """
    applies a user-provided function designed to inject an external update to InstructionGenerators

    :param fn: the function which applies an update or returns None for no update
    :param sim: the simulation state, which will not be modified but available to the update function
    :return: the updated list of InstructionGenerators
    """

    def _inner(
        acc: UserProvidedUpdateAccumulator, i: InstructionGenerator
    ) -> UserProvidedUpdateAccumulator:
        try:
            result = fn(i, sim)
            if not result:
                return acc.apply_updated_instruction_generator(i)
            else:
                return acc.apply_updated_instruction_generator(result)
        except Exception as e:
            raise e

    return _inner
