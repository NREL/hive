from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, TYPE_CHECKING, Callable, NamedTuple
import logging
import immutables

from hive.dispatcher.instruction.instruction_interface import Instruction
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.model.vehicle import Vehicle
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
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

    def _sort_by_vehicle_state(vs: Tuple[Vehicle, ...]) -> Tuple[Vehicle, ...]:
        """
        a one-pass partitioning to place ChargeQueueing agents after their non-ChargeQueueing friends
        and to sort the charge queueing agents by their enqueue_time

        if we need additional sort criteria for future VehicleStates we may need to
        instead call sim.get_vehicles with a sort_key function in place of this shortcut

        :param vs: the vehicles
        :return: the vehicles with all ChargeQueueing vehicles at the tail
        """
        charge_queueing_vehicles, other_vehicles = TupleOps.partition(lambda v: isinstance(v, ChargeQueueing), vs)
        sorted_charge_queueing_vehicles = tuple(sorted(charge_queueing_vehicles, key=lambda v: v.enqueue_time))
        return other_vehicles + sorted_charge_queueing_vehicles

    vehicles = _sort_by_vehicle_state(simulation_state.get_vehicles())
    next_state = ft.reduce(_step_vehicle, vehicles, simulation_state)

    return simulation_state_ops.tick(next_state)


def apply_instructions(simulation_state: SimulationState,
                       env: Environment,
                       instructions: immutables.Map[VehicleId, Instruction]) -> SimulationState:
    """
    this helper function takes a map with one instruction per agent at most, and attempts to apply each
    instruction to the simulation, managing the instruction's externalities, and managing failure.

    :param simulation_state: the current simulation state
    :param env: the sim environment
    :param instructions: all instructions to add at this time step
    :return: the simulation state modified by all successful Instructions
    """

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
