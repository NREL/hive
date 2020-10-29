from __future__ import annotations
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.driver_state.driver_state import DriverState
from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import ChargeBaseInstruction

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.util.typealiases import ScheduleId


class AutonomousAvailable(NamedTuple, DriverState):
    """
    an autonomous driver that is available to work
    """
    attributes: AutonomousDriverAttributes = AutonomousDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return None

    @property
    def available(cls):
        return True

    def generate_instruction(
            self,
            sim: SimulationState,
            env: Environment,
            previous_instructions: Optional[Tuple[Instruction, ...]] = None,
    ) -> Optional[Instruction]:

        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if isinstance(my_vehicle.vehicle_state, ReserveBase):
            # if this driver is at a base, it will attempt to charge its vehicle
            my_base = sim.bases.get(my_vehicle.vehicle_state.base_id)
            if not my_base.station_id:
                return None

            my_station = sim.stations.get(my_base.station_id)
            my_mechatronics = env.mechatronics.get(my_vehicle.mechatronics_id)

            chargers = tuple(filter(
                lambda c: my_mechatronics.valid_charger(c),
                [env.chargers[cid] for cid in my_station.total_chargers.keys()]
            ))

            if not chargers:
                return None

            # take the lowest power charger
            charger = sorted(chargers, key=lambda c: c.rate)[0]
            i = ChargeBaseInstruction(self.attributes.vehicle_id, my_base.base_id, charger.id)
        else:
            i = None

        return i

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        # there is no other state for an autonomous driver, so, this is a noop
        return None, sim
