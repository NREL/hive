from __future__ import annotations

from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    return_to_base,
    set_to_reserve,
    charge_at_base,
    charge_at_station,
    send_vehicle_to_field,
    sit_idle,
)
from hive.external.demo_base_target.fleet_targets import FleetTarget
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
    fleet_target: FleetTarget = FleetTarget()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[DeluxeFleetManager, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """
        instructions = ()

        if simulation_state.sim_time % (10*60) != 0:
            # only try to manage fleet at 10 minute intervals
            return self, instructions, ()

        def is_active(vstate: VehicleState) -> bool:
            return isinstance(vstate, Idle) or \
                   isinstance(vstate, Repositioning) or \
                   isinstance(vstate, DispatchTrip) or \
                   isinstance(vstate, ServicingTrip)

        def is_active_ready(vstate: VehicleState) -> bool:
            return isinstance(vstate, Idle) or \
                   isinstance(vstate, Repositioning)

        base_charge_vehicles = [v for v in simulation_state.vehicles.values()
                                if isinstance(v.vehicle_state, ChargingBase)]
        station_charge_vehicles = [v for v in simulation_state.vehicles.values()
                                   if isinstance(v.vehicle_state, ChargingStation)]
        reserve_vehicles = [v for v in simulation_state.vehicles.values()
                            if isinstance(v.vehicle_state, ReserveBase)]
        active_vehicles = [v for v in simulation_state.vehicles.values()
                           if is_active(v.vehicle_state)]
        active_ready_vehicles = [v for v in simulation_state.vehicles.values()
                                 if is_active_ready(v.vehicle_state)]

        n_base_charging = len(base_charge_vehicles)
        n_station_charging = len(station_charge_vehicles)
        n_active = len(active_vehicles)

        base_charge_target = int(self.fleet_target.get_base_target(simulation_state.sim_time))
        station_charge_target = int(self.fleet_target.get_station_target(simulation_state.sim_time))
        active_target = int(self.fleet_target.get_active_target(simulation_state.sim_time))

        base_charge_diff = base_charge_target - n_base_charging
        station_charge_diff = station_charge_target - n_station_charging
        active_diff = active_target - n_active

        if base_charge_diff < 0:
            # we have more charging vehicles than we need
            reserve_instructions = set_to_reserve(abs(base_charge_diff), base_charge_vehicles, simulation_state)
            instructions = instructions + reserve_instructions
        elif base_charge_diff > 0:
            # we don't have enough charging vehicles
            charge_instructions = charge_at_base(base_charge_diff, reserve_vehicles, simulation_state)
            instructions = instructions + charge_instructions

        if station_charge_diff < 0:
            # we have more station charging than we want
            idle_instructions = sit_idle(abs(station_charge_diff), station_charge_vehicles)
            instructions = instructions + idle_instructions
        elif station_charge_diff > 0:
            # we need more vehicles charging at a station
            charge_instructions = charge_at_station(station_charge_diff, active_ready_vehicles, simulation_state)
            instructions = instructions + charge_instructions

        if active_diff < 0:
            # we have more active vehicles than we need
            active_instructions = return_to_base(abs(active_diff), active_vehicles, simulation_state)
            instructions = instructions + active_instructions
        elif active_diff > 0:
            # we we need more active vehicles in the field
            repos_instructions = send_vehicle_to_field(active_diff, reserve_vehicles, simulation_state)
            instructions = instructions + repos_instructions

        return self, instructions, ()
