from __future__ import annotations

import logging
from typing import Tuple, NamedTuple, TYPE_CHECKING

import immutables

if TYPE_CHECKING:
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.dispatcher.managers.manager_interface import ManagerInterface
    from hive.util.typealiases import Report

from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.util.helpers import DictOps

log = logging.getLogger(__name__)


class BasicDispatcher(NamedTuple, DispatcherInterface):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """
    managers: Tuple[ManagerInterface, ...]

    def generate_instructions(self,
                              simulation_state: 'SimulationState',
                              ) -> Tuple[DispatcherInterface, InstructionMap, Tuple[Report, ...]]:

        instruction_map = immutables.Map()
        reports = ()
        updated_managers = ()

        for manager in self.managers:

            new_manager, new_instructions, manager_reports = manager.generate_instructions(simulation_state)

            reports = reports + manager_reports

            for instruction in new_instructions:
                instruction_map = DictOps.add_to_dict(instruction_map, instruction.vehicle_id, instruction)

            updated_managers = updated_managers + (new_manager,)

        return self._replace(managers=updated_managers), instruction_map, reports
