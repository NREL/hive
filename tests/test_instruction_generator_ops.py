from unittest import TestCase

from nrel.hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_to_dispatch_to_station,
)
from nrel.hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from nrel.hive.resources.mock_lobster import (
    mock_env,
    mock_ice,
    mock_sim,
    mock_station,
    mock_vehicle,
)


class TestInstructionGenerators(TestCase):
    def test_dispatch_station_ops_mismatch_charger_queue(self):
        """
        this tests the helper function instruct_vehicles_to_dispatch_to_station.

        here we create a simulation in which the chargers that exist in the sim can't be used by the
        vehicle; this edge case should not fail but rather result in zero instructions; given the
        logic splits for each ChargingSearchType, we test ChargingSearchType.NEAREST_SHORTEST_QUEUE
        """
        station = mock_station()
        ice_mechatronics = mock_ice()
        vehicle = mock_vehicle(
            mechatronics=ice_mechatronics,
            soc=0.1,
        )

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env(mechatronics={ice_mechatronics.mechatronics_id: ice_mechatronics})

        instructions = instruct_vehicles_to_dispatch_to_station(
            n=1,
            max_search_radius_km=10,
            vehicles=(vehicle,),
            simulation_state=sim,
            environment=env,
            target_soc=0.2,
            charging_search_type=ChargingSearchType.NEAREST_SHORTEST_QUEUE,
        )

        self.assertEqual(len(instructions), 0, "should not have generated any instructions")

    def test_dispatch_station_ops_mismatch_charger_shortest_time(self):
        """
        this tests the helper function instruct_vehicles_to_dispatch_to_station.

        here we create a simulation in which the chargers that exist in the sim can't be used by the
        vehicle; this edge case should not fail but rather result in zero instructions; given the
        logic splits for each ChargingSearchType, we test ChargingSearchType.SHORTEST_TIME_TO_CHARGE
        """
        station = mock_station()
        mechatronics = mock_ice()
        vehicle = mock_vehicle(
            mechatronics=mechatronics,
            soc=0.1,
        )

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env(mechatronics={mechatronics.mechatronics_id: mechatronics})

        instructions = instruct_vehicles_to_dispatch_to_station(
            n=1,
            max_search_radius_km=10,
            vehicles=(vehicle,),
            simulation_state=sim,
            environment=env,
            target_soc=0.2,
            charging_search_type=ChargingSearchType.SHORTEST_TIME_TO_CHARGE,
        )

        self.assertEqual(len(instructions), 0, "should not have generated any instructions")
