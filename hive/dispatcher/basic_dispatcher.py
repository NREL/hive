from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

import immutables

if TYPE_CHECKING:
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.dispatcher.instructors.instructor_interface import InstructorInterface
    from hive.util.typealiases import Report

from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.util.helpers import DictOps

log = logging.getLogger(__name__)


class BasicDispatcher(NamedTuple, DispatcherInterface):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """
    manager: ManagerInterface

    instructors: Tuple[InstructorInterface, ...]

    @classmethod
    def build(cls,
              manager: ManagerInterface,
              instructors: Tuple[InstructorInterface, ...],
              ) -> BasicDispatcher:

        return BasicDispatcher(
            manager=manager,
            instructors=instructors,
        )

    def generate_instructions(self,
                              simulation_state: 'SimulationState',
                              ) -> Tuple[DispatcherInterface, InstructionMap, Tuple[Report, ...]]:

        instruction_map = immutables.Map()
        reports = ()

        updated_manager, fleet_targets, manager_reports = self.manager.generate_fleet_targets(simulation_state)

        reports = reports + manager_reports
        updated_dispatcher = self._replace(manager=updated_manager)

        for fleet_target in fleet_targets:
            fleet_target_instructions = fleet_target.apply_target(simulation_state)
            for v_id, instruction in fleet_target_instructions.items():
                instruction_map = DictOps.add_to_dict(instruction_map, v_id, instruction)

        updated_instructors = ()

        for instructor in self.instructors:
            instructor_result = instructor.generate_instructions(simulation_state, instruction_map)
            new_instructor, new_instructions, instructor_reports = instructor_result

            reports = reports + instructor_reports

            instruction_map = DictOps.merge_dicts(instruction_map, new_instructions)

            updated_instructors = updated_instructors + (new_instructor,)

        return updated_dispatcher._replace(instructors=updated_instructors), instruction_map, reports
