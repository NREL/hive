from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from hive.dispatcher.instruction_generator.instruction_generator_ops import get_nearest_valid_station_distance

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.vehicle.vehicle import Vehicle
    from hive.runner.environment import Environment

from typing import NamedTuple

from hive.util.units import Kilometers
from hive.util.typealiases import BaseId


class HumanUnavailableChargeParameters(NamedTuple):
    remaining_range_target: Optional[Kilometers] = None

    @classmethod
    def build(cls,
              vehicle: Vehicle,
              home_base_id: BaseId,
              sim: SimulationState,
              env: Environment) -> HumanUnavailableChargeParameters:
        """
        builds the parameters used to track our vehicle's need for charging. captures
        distance to home, optional distance to a charger tomorrow (in the case of no home charging),
        along with a distance buffer. if those distances exceed the current engine's remaining range,
        we store our range target as a state parameter.

        :param vehicle: the vehicle associated with these parameters
        :param home_base_id: the home base for this driver
        :param sim: the simulation state
        :param env: the simulation environment
        :return: charge parameters if the vehicle needs to charge on the way home, otherwise None
        """

        my_base = sim.bases.get(home_base_id)
        my_mechatronics = env.mechatronics.get(vehicle.mechatronics_id)

        if my_base is None or my_mechatronics is None:
            return HumanUnavailableChargeParameters()
        else:
            remaining_range = my_mechatronics.range_remaining_km(vehicle)
            range_to_get_home = sim.road_network.distance_by_geoid_km(vehicle.geoid, my_base.geoid)
            buffer = env.config.dispatcher.charging_range_km_threshold

            # if we do not have home charging, then we must charge at least enough to reach a charger tomorrow
            range_to_charger_tomorrow = get_nearest_valid_station_distance(
                max_search_radius_km=env.config.dispatcher.max_search_radius_km,
                vehicle=vehicle,
                geoid=my_base.geoid,
                simulation_state=sim,
                environment=env,
                target_soc=env.config.dispatcher.ideal_fastcharge_soc_limit,
                charging_search_type=env.config.dispatcher.charging_search_type
            ) if my_base.station_id is None else 0.0

            # determine if we have a charge target
            total_range_required = range_to_get_home + range_to_charger_tomorrow + buffer
            charge_target = total_range_required if total_range_required > remaining_range else None
            charge_params = HumanUnavailableChargeParameters() if charge_target is None else HumanUnavailableChargeParameters(charge_target)

            return charge_params
