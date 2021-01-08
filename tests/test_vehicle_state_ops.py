from unittest import TestCase

from hive.model.energy.energytype import EnergyType
from hive.state.vehicle_state import vehicle_state_ops
from tests.mock_lobster import *


class TestVehicleStateOps(TestCase):

    def test_move(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.7579, -104.978, 15)
        sim = mock_sim(sim_timestep_duration_seconds=10)
        somewhere_link = sim.road_network.stationary_location_from_geoid(somewhere)
        somewhere_else_link = sim.road_network.stationary_location_from_geoid(somewhere_else)
        route = sim.road_network.route(somewhere_link, somewhere_else_link)
        state = Repositioning(DefaultIds.mock_vehicle_id(), route)
        vehicle = mock_vehicle_from_geoid(geoid=somewhere, vehicle_state=state)
        e1, sim_with_veh = simulation_state_ops.add_vehicle(sim, vehicle)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()

        self.assertIsNotNone(sim_with_veh, "test invariant failed")

        error, mr1 = vehicle_state_ops.move(sim_with_veh, env, vehicle.id, route)
        if error:
            self.fail(error)

        result_sim = mr1.sim

        moved_vehicle = result_sim.vehicles.get(vehicle.id)
        soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(moved_vehicle)

        self.assertLess(soc, 1, "should have used 1 unit of mock energy")
        self.assertNotEqual(somewhere, moved_vehicle.geoid, "should not be at the same location")
        self.assertNotEqual(somewhere, moved_vehicle.link.start, "link start location should not be the same")

    def test_charge(self):

        state = ChargingBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), mock_dcfc_charger_id())
        veh = mock_vehicle_from_geoid(vehicle_state=state, soc=0.5)
        sta = mock_station_from_geoid()
        bas = mock_base_from_geoid(station_id=sta.id)
        sim = mock_sim(
            vehicles=(veh,),
            stations=(sta,),
            bases=(bas,),
            sim_timestep_duration_seconds=1
        )
        env = mock_env()

        error, result = vehicle_state_ops.charge(sim, env, veh.id, sta.id, mock_dcfc_charger_id())
        if error:
            self.fail(error)

        updated_veh = result.vehicles.get(veh.id)

        self.assertGreater(
            updated_veh.energy[EnergyType.ELECTRIC],
            veh.energy[EnergyType.ELECTRIC],
            msg="should have charged")

    def test_charge_when_full(self):

        state = ChargingBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), mock_dcfc_charger_id())
        veh = mock_vehicle_from_geoid(vehicle_state=state, soc=1.0)
        sta = mock_station_from_geoid()
        bas = mock_base_from_geoid(station_id=sta.id)
        sim = mock_sim(
            vehicles=(veh,),
            stations=(sta,),
            bases=(bas,),
            sim_timestep_duration_seconds=1
        )
        env = mock_env()

        error, result = vehicle_state_ops.charge(sim, env, veh.id, sta.id, mock_dcfc_charger_id())

        self.assertIsNotNone(error)
        self.assertIsNone(result)
