from __future__ import annotations

from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    return_to_base,
    set_to_reserve,
    charge_at_base,
    send_vehicle_to_field,
)
from hive.external.demo_base_target.temp_base_target import BaseTarget
from hive.state.vehicle_state import *
from hive.state.vehicle_state import (
    ReserveBase,
    ChargingBase,
)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

log = logging.getLogger(__name__)


class DeluxeFleetManager(NamedTuple, InstructionGenerator):
    """
    The deluxe fleet manager combines the objectives of meeting a base charging target and meeting an
    active vehicle target.

    At each timestep, the manager attempts to balance the number of active vehicles and base charging vehicles:
     - If there are too many active vehicles, the vehicles return to base and join the reserves.
     - If there are not enough active vehicles, the manager randomly repositions the base vehicles choosing those with
        the highest SOC first.
     - If there are not enough vehicles charging, the manager pull vehicles from the reserves to charge.
     - If there are too many vehicles charging, the manager instructs chargings vehicles to join the reserves.

    TODO: this model could benefit from considering the active vehicles and the base vehicles together when making
      decisions. For example, when trying to charge vehicles, the model could first check the reserves and then, if
      there are not enough vehicles to meet the target, it could consider active vehicles.

    TODO: we should add a target for vehicles charging at a fast charge station. This will get us close to demoing
      a smart charging scenario.
    """
    demand_forecaster: ForecasterInterface
    base_target: BaseTarget = BaseTarget()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[DeluxeFleetManager, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """
        updated_forecaster, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        def is_active(vstate: VehicleState) -> bool:
            return isinstance(vstate, Idle) or \
                   isinstance(vstate, Repositioning)

        instructions = ()

        base_charge_vehicles = [v for v in simulation_state.vehicles.values()
                                if isinstance(v.vehicle_state, ChargingBase)]
        reserve_vehicles = [v for v in simulation_state.vehicles.values()
                            if isinstance(v.vehicle_state, ReserveBase)]
        active_vehicles = [v for v in simulation_state.vehicles.values()
                           if is_active(v.vehicle_state)]

        n_charging = len(base_charge_vehicles)
        n_active = len(active_vehicles)

        charge_target = int(self.base_target.get_target(simulation_state.sim_time))
        active_target = future_demand.value

        charge_diff = charge_target - n_charging
        active_diff = active_target - n_active

        if active_diff < 0:
            # we have more active vehicles than we need
            if charge_diff < 0:
                # we have more charging vehicles than we need
                # ACTION: send active vehicles to base, send charging vehicles to reserve
                active_instructions = return_to_base(abs(active_diff), active_vehicles, simulation_state)
                reserve_instructions = set_to_reserve(abs(charge_diff), base_charge_vehicles, simulation_state)
                instructions = instructions + active_instructions + reserve_instructions
            elif charge_diff > 0:
                # we don't have enough charging vehicles
                # ACTION: take reserve and charge them, send active vehicles to base
                active_instructions = return_to_base(abs(active_diff), active_vehicles, simulation_state)
                charge_instructions = charge_at_base(abs(charge_diff), reserve_vehicles, simulation_state)
                instructions = instructions + active_instructions + charge_instructions
            else:
                # ACTION: just send active vehicles home
                active_instructions = return_to_base(abs(active_diff), active_vehicles, simulation_state)
                instructions = instructions + active_instructions
        elif active_diff > 0:
            # we need more vehicles in the field
            if charge_diff < 0:
                # we have more charging vehicles than we need
                # ACTION: send highest soc vehicles out to field
                repos_instructions = send_vehicle_to_field(active_diff, base_charge_vehicles, simulation_state)
                instructions = instructions + repos_instructions
            elif charge_diff > 0:
                # we don't have enough charging vehicles
                # ACTION: send vehicles to field first then charge remaining vehicles
                charge_instructions = charge_at_base(charge_diff, reserve_vehicles, simulation_state)
                repos_instructions = send_vehicle_to_field(active_diff, reserve_vehicles, simulation_state)
                instructions = instructions + charge_instructions + repos_instructions
            else:
                repos_instructions = send_vehicle_to_field(active_diff, reserve_vehicles, simulation_state)
                instructions = instructions + repos_instructions

        return self._replace(demand_forecaster=updated_forecaster), instructions, ()
