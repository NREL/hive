from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import (
    DispatchBaseInstruction, ReserveBaseInstruction,
)
from hive.reporting.driver_event_ops import driver_schedule_event, ScheduleEventType
from hive.state.driver_state.driver_instruction_ops import (
    human_charge_at_home,
    idle_if_at_soc_limit,
    human_look_for_requests,
    human_go_home)
from hive.state.driver_state.driver_state import DriverState
from hive.state.driver_state.human_driver_state.human_driver_attributes import HumanDriverAttributes
from hive.state.driver_state.human_driver_state.human_unavailable_charge_parameters import HumanUnavailableChargeParameters
from hive.state.vehicle_state.charging_base import ChargingBase
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.state.vehicle_state.dispatch_base import DispatchBase
from hive.state.vehicle_state.dispatch_station import DispatchStation
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.util import SimulationStateError, BaseId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.util.typealiases import ScheduleId

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

    @property
    def allows_pooling(cls):
        return cls.attributes.allows_pooling

    @property
    def home_base_id(cls) -> Optional[BaseId]:
        return cls.attributes.home_base_id

    def generate_instruction(
            self,
            sim: SimulationState,
            env: Environment,
            previous_instructions: Optional[Tuple[Instruction, ...]] = None,
    ) -> Optional[Instruction]:

        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)
        if not my_vehicle:
            log.error(f"could not find vehicle {self.attributes.vehicle_id} in simulation")

        state = my_vehicle.vehicle_state

        # once the vehicle is available it should reposition to seek out requests.
        if isinstance(state, ReserveBase) or isinstance(state, ChargingBase):
            # if the driver is sitting at home we try to seek out requests
            return human_look_for_requests(my_vehicle, sim)
        elif isinstance(my_vehicle.vehicle_state, ChargingStation):
            # if the driver is charging we unplug if we reach the soc limit
            return idle_if_at_soc_limit(my_vehicle, env)
        elif isinstance(state, Idle):
            # if the driver has been idle for longer than the idle_time_out_seconds limit, we move to seek out greener
            # pastures
            if state.idle_duration > env.config.dispatcher.idle_time_out_seconds:
                return human_look_for_requests(my_vehicle, sim)
        else:
            return None

    def update(self,
               sim: SimulationState,
               env: Environment
               ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
            state_name = self.__class__.__name__
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found; context: update {state_name} driver state")
            return error, None
        else:
            # log transition
            report = driver_schedule_event(sim, env, vehicle, ScheduleEventType.OFF)
            env.reporter.file_report(report)

            # transition to unavailable
            charge_params = HumanUnavailableChargeParameters.build(vehicle, self.attributes.home_base_id, sim, env)
            next_state = HumanUnavailable(self.attributes, charge_params)
            result = DriverState.apply_new_driver_state(sim,
                                                        self.attributes.vehicle_id,
                                                        next_state)
            return result


class HumanUnavailable(NamedTuple, DriverState):
    """
    a human driver that is not available to work
    """
    attributes: HumanDriverAttributes
    charge_params: HumanUnavailableChargeParameters = HumanUnavailableChargeParameters()

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return cls.attributes.schedule_id

    @property
    def available(cls):
        return False

    @property
    def allows_pooling(cls):
        return cls.attributes.allows_pooling

    @property
    def home_base_id(cls) -> Optional[BaseId]:
        return cls.attributes.home_base_id

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
            return None
        elif not my_base:
            log.error(f"could not find base {self.attributes.home_base_id} in simulation "
                      f"for veh {self.attributes.vehicle_id}")
            return None
        else:
            at_home = my_base.geoid == my_vehicle.geoid
            my_mechatronics = env.mechatronics.get(my_vehicle.mechatronics_id)

            if not at_home:
                if isinstance(my_vehicle.vehicle_state, DispatchBase):
                    # stick with the plan
                    return None
                if isinstance(my_vehicle.vehicle_state, DispatchStation) or isinstance(my_vehicle.vehicle_state, ChargingStation):
                    remaining_range = my_mechatronics.range_remaining_km(my_vehicle)
                    if self.charge_params.remaining_range_target and remaining_range < self.charge_params.remaining_range_target:
                        # stick with the plan (charging)
                        return None
                    else:
                        # we have charged to our charge target, or, have no charging target
                        instruction = DispatchBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id)
                        return instruction
                else:
                    # go home or charge on the way home if you need to
                    return human_go_home(my_vehicle, my_base, sim, env)
            else:
                not_full = my_mechatronics.fuel_source_soc(my_vehicle) < env.config.dispatcher.ideal_fastcharge_soc_limit
                if not_full and my_base.station_id and not isinstance(my_vehicle.vehicle_state, ChargingBase):
                    # otherwise, if we're at home and we have a plug, we try to charge to full
                    return human_charge_at_home(my_vehicle, my_base, sim, env)
                elif isinstance(my_vehicle.vehicle_state, Idle):
                    # finally, if we're at home and idling, we turn the vehicle off
                    return ReserveBaseInstruction(self.attributes.vehicle_id, self.attributes.home_base_id)
                else:
                    return None

    def update(self,
               sim: 'SimulationState',
               env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        test that the agent is unavailable to work. if not, transition to an available state.


        :param sim: the current simulation state
        :param env: the simulation environment
        :return: the updated simulation state with a possible state transition for this driver
        """
        schedule_function = env.schedules.get(self.attributes.schedule_id)
        vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if not vehicle:
            state_name = self.__class__.__name__
            error = SimulationStateError(f"vehicle {self.attributes.vehicle_id} not found; context: update {state_name} driver state")
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
