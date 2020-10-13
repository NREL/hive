from unittest import TestCase

from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_at_base_to_charge,
    instruct_vehicles_to_dispatch_to_station,
)
from hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from tests.mock_lobster import *


class TestInstructionGenerators(TestCase):
    def test_base_charge_ops_mismatched_charger(self):
        station = mock_station()
        base = mock_base(station_id=station.id)
        mechatronics = mock_ice()
        vehicle = mock_vehicle(
            mechatronics=mechatronics,
            vehicle_state=ReserveBase(vehicle_id=DefaultIds.mock_vehicle_id(), base_id=base.id)
        )

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,),
        )
        env = mock_env(mechatronics={mechatronics.mechatronics_id: mechatronics})

        instructions = instruct_vehicles_at_base_to_charge(
            vehicles=(vehicle,),
            simulation_state=sim,
            environment=env,
        )

        self.assertEqual(len(instructions), 0, "should not have generated any instructions")

    def test_base_charge_ops_no_charger(self):
        station = mock_station(chargers={"non-standard-charger": 1})
        base = mock_base(station_id=station.id)
        vehicle = mock_vehicle(
            vehicle_state=ReserveBase(vehicle_id=DefaultIds.mock_vehicle_id(), base_id=base.id)
        )

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,),
        )
        env = mock_env()

        instructions = instruct_vehicles_at_base_to_charge(
            vehicles=(vehicle,),
            simulation_state=sim,
            environment=env,
        )

        self.assertEqual(len(instructions), 0, "should not have generated any instructions")

    def test_base_charge_ops_fast_charger(self):
        station = mock_station()
        base = mock_base(station_id=station.id)
        vehicle = mock_vehicle(
            vehicle_state=ReserveBase(vehicle_id=DefaultIds.mock_vehicle_id(), base_id=base.id)
        )

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,),
        )
        env = mock_env()

        instructions = instruct_vehicles_at_base_to_charge(
            vehicles=(vehicle,),
            simulation_state=sim,
            environment=env,
        )

        self.assertEqual(len(instructions), 1, "should have generated one instruction")
        self.assertEqual(instructions[0].charger_id, mock_dcfc_charger_id(), "should have picked DCFC charger")

    def test_dispatch_station_ops_mismatch_charger_queue(self):
        """
        this tests the helper function instruct_vehicles_to_dispatch_to_station.

        here we create a simulation in which the chargers that exist in the sim can't be used by the
        vehicle; this edge case should not fail but rather result in zero instructions; given the
        logic splits for each ChargingSearchType, we test ChargingSearchType.NEAREST_SHORTEST_QUEUE here
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
            max_search_radius_km=100,
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
        logic splits for each ChargingSearchType, we test ChargingSearchType.SHORTEST_TIME_TO_CHARGE here
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
