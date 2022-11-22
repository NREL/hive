from typing import Callable

from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.util.typealiases import VehicleId

# if we create a DriverId type, and it has a lookup table on SimulationState, we may
# want to change this from VehicleId to DriverId
ScheduleFunction = Callable[[SimulationState, VehicleId], bool]
