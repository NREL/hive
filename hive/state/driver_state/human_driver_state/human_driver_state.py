from __future__ import annotations
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

import h3
import logging
import random

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import (
    DispatchBaseInstruction,
    ChargeBaseInstruction,
    RepositionInstruction,
)
from hive.reporting.driver_event_ops import driver_schedule_event, ScheduleEventType
from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
from hive.state.vehicle_state.dispatch_base import DispatchBase
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.vehicle_state.charging_base import ChargingBase
from hive.state.vehicle_state.idle import Idle
from hive.util import SimulationStateError

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.runner.environment import Environment
    from hive.util.typealiases import ScheduleId, GeoId

log = logging.getLogger(__name__)

# these two classes (HumanAvailable, HumanUnavailable) are in the same file in order to avoid circular references


class HumanAvailable(NamedTuple, DriverState):
    """
    a human driver that is available to work as the current simulation state is consistent with
    the driver's schedule function
    """
    attributes: HumanDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return cls.attributes.schedule_id

    @property
    def available(cls):
        return True

    def generate_instruction(
            self,
            sim: SimulationState,
            env: Environment,
            previous_instructions: Optional[Tuple[Instruction, ...]] = None,
    ) -> Optional[Instruction]:
        def _get_reposition_location() -> Optional[str]:
            if len(sim.r_search) == 0:
                # no requests in system, do nothing
                return None
            else:
                # find the most dense request search hex and sends vehicles to the center
                best_search_hex = sorted(
                    [(k, len(v)) for k, v in sim.r_search.items()], key=lambda t: t[1],
                    reverse=True
                )[0][0]
            destination = h3.h3_to_center_child(best_search_hex, sim.sim_h3_location_resolution)
            return destination

        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)
        if not my_vehicle:
            log.error(f"could not find vehicle {self.attributes.vehicle_id} in simulation")

        state = my_vehicle.vehicle_state

        i = None

        # once the vehicle is available it should reposition to seek out requests.
        # if the vehicle is at home, it should reposition;
        # and, if the vehicle has been idle for 30 minutes, it should reposition;
        if isinstance(state, ReserveBase) or isinstance(state, ChargingBase):
            dest = _get_reposition_location()
            if dest:
                i = RepositionInstruction(self.attributes.vehicle_id, _get_reposition_location())
        elif isinstance(state, Idle):
            dest = _get_reposition_location()
            if state.idle_duration > 1800 and dest:
                i = RepositionInstruction(self.attributes.vehicle_id, _get_reposition_location())

        return i

    def update(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        """
        test that the agent is available to work. if unavailable, transition to an unavailable state.


        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if not schedule_function or schedule_function(sim, self.attributes.vehicle_id):
            # stay available
            return None, sim
        elif not vehicle:
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found")
            return error, None
        else:
            # log transition
            report = driver_schedule_event(sim, env, vehicle, ScheduleEventType.OFF)
            env.reporter.file_report(report)

            # transition to unavailable
            next_state = HumanUnavailable(self.attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.attributes.vehicle_id,
                                                        next_state)
            return result


class HumanUnavailable(NamedTuple, DriverState):
    """
    a human driver that is available to work
    """
    attributes: HumanDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return cls.attributes.schedule_id

    @property
    def available(cls):
        return False

    def generate_instruction(
            self,
            sim: SimulationState,
            env: Environment,
            previous_instructions: Optional[Tuple[Instruction, ...]] = None,
    ) -> Optional[Instruction]:
        """
        while in this state, the driver checks the vehicle location; if the vehicle is not at the home base,
        a new instruction is generated to send the vehicle home.


        :param sim:
        :param env:
        :param previous_instructions:
        :return:
        """

        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)
        my_base = sim.bases.get(self.attributes.home_base_id)

        if not my_vehicle:
            log.error(f"could not find vehicle {self.attributes.vehicle_id} in simulation")
        if not my_base:
            log.error(f"could not find base {self.attributes.home_base_id} in simulation "
                      f"for veh {self.attributes.vehicle_id}")

        def at_home() -> bool:
            return my_base.geoid == my_vehicle.geoid

        if not at_home() and not isinstance(my_vehicle.vehicle_state, DispatchBase):
            i = DispatchBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id)
        elif my_base.station_id and not isinstance(my_vehicle.vehicle_state, ChargingBase) and at_home():
            my_station = sim.stations.get(my_base.station_id)
            if not my_station:
                log.error(f"could not find station {my_base.station_id} for base {self.attributes.home_base_id}")
                return None

            my_mechatronics = env.mechatronics.get(my_vehicle.mechatronics_id)

            chargers = tuple(filter(
                lambda c: my_mechatronics.valid_charger(c),
                [env.chargers[cid] for cid in my_station.total_chargers.keys()]
            ))
            if not chargers:
                i = None
            else:
                # take the lowest power charger
                charger = sorted(chargers, key=lambda c: c.rate)[0]
                i = ChargeBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id, charger.id)
        else:
            i = None

        return i

    def update(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        """
        test that the agent is unavailable to work. if not, transition to an available state.


        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if not vehicle:
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found")
            return error, None
        elif schedule_function and schedule_function(sim, self.attributes.vehicle_id):
            # log transition
            report = driver_schedule_event(sim, env, vehicle, ScheduleEventType.ON)
            env.reporter.file_report(report)

            # transition to available, because of one of these reasons:
            #   being unavailable but not having a schedule is invalid.
            #   the schedule function returns true, so, we should be activated
            next_state = HumanAvailable(self.attributes)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.attributes.vehicle_id,
                                                        next_state)
            return result
        else:
            # stay unavailable
            return None, sim
