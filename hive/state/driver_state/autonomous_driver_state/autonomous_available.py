from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import ChargeBaseInstruction, DispatchBaseInstruction
from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
from hive.state.driver_state.driver_state import DriverState
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.util import H3Ops, TupleOps

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.util.typealiases import ScheduleId

log = logging.getLogger(__name__)


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
        i = None

        if isinstance(my_vehicle.vehicle_state, ReserveBase):
            # if this driver is at a base, it will attempt to charge its vehicle
            my_base = sim.bases.get(my_vehicle.vehicle_state.base_id)
            if not my_base.station_id:
                return None

            my_station = sim.stations.get(my_base.station_id)
            if not my_station:
                log.error(f"could not find station {my_base.station_id} for base {my_base.base_id}")
                return None
            my_mechatronics = env.mechatronics.get(my_vehicle.mechatronics_id)

            chargers = tuple(filter(
                lambda c: my_mechatronics.valid_charger(c),
                [env.chargers[cid] for cid in my_station.total_chargers.keys()]
            ))

            if not chargers:
                return None

            # take the lowest power charger
            charger = sorted(chargers, key=lambda c: c.rate)[0]
            i = ChargeBaseInstruction(self.attributes.vehicle_id, my_base.id, charger.id)
        elif isinstance(my_vehicle.vehicle_state, Idle):
            if my_vehicle.vehicle_state.idle_duration > 600:
                # timeout after 10 minutes of being idle
                bases_at_play = TupleOps.flatten(
                    tuple(sim.get_bases(membership_id=m) for m in my_vehicle.membership.memberships)
                )
                best_base = H3Ops.nearest_entity_by_great_circle_distance(
                    geoid=my_vehicle.geoid,
                    entities=bases_at_play,
                    entity_search=sim.b_search,
                    sim_h3_search_resolution=sim.sim_h3_search_resolution,
                    max_search_distance_km=env.config.dispatcher.max_search_radius_km,
                )

                if best_base:
                    i = DispatchBaseInstruction(self.attributes.vehicle_id, best_base.id)

        return i

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        # there is no other state for an autonomous driver, so, this is a noop
        return None, sim
