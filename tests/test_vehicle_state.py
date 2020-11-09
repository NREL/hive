from unittest import TestCase

from hive.state.entity_state import entity_state_ops
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
from hive.state.vehicle_state.out_of_service import OutOfService
from tests.mock_lobster import *


class TestVehicleState(TestCase):

    ####################################################################################################################
    # ChargingStation ##################################################################################################
    ####################################################################################################################

    def test_charging_station_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingStation, "should be in a charging state")
        self.assertEquals(available_chargers, 0, "should have claimed the only DCFC charger_id")

    def test_charging_station_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        station = mock_station(membership=Membership.single_membership("lyft"))

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, mock_dcfc_charger_id())
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should return none for updated sim")

    def test_charging_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, charger)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.exit(updated_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingStation, "should still be in a charging state")
        self.assertEquals(available_chargers, 1, "should have returned the only DCFC charger_id")

    def test_charging_station_update(self):
        vehicle = mock_vehicle(soc=0.5)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertAlmostEqual(
            first=updated_vehicle.energy[EnergyType.ELECTRIC],
            second=vehicle.energy[EnergyType.ELECTRIC] + 0.76,
            places=2,
            msg="should have charged for 60 seconds")

    def test_charging_station_update_terminal(self):
        vehicle = mock_vehicle(soc=1)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_station = sim_updated.stations.get(station.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "vehicle should be in idle state")
        self.assertEquals(updated_station.available_chargers.get(charger), 1, "should have returned the charger_id")

    def test_charging_station_enter_with_no_station(self):
        vehicle = mock_vehicle(soc=0.99)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_enter_with_no_vehicle(self):
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            stations=(station,),
        )
        env = mock_env()

        state = ChargingStation(DefaultIds.mock_vehicle_id(), DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_invalid_charger(self):
        station = mock_station()
        charger = mock_dcfc_charger_id()
        vehicle = mock_vehicle(mechatronics=mock_ice())
        sim = mock_sim(
            stations=(station,),
            vehicles=(vehicle,),
        )
        env = mock_env(mechatronics={DefaultIds.mock_mechatronics_ice_id(): mock_ice()})

        state = ChargingStation(DefaultIds.mock_vehicle_id(), DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_subsequent_charge_instructions(self):
        vehicle = mock_vehicle()
        station = mock_station(chargers=immutables.Map({mock_l2_charger_id(): 1, mock_dcfc_charger_id(): 1}))
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, station.id, mock_dcfc_charger_id())
        err1, sim1 = state.enter(sim, env)
        self.assertIsNone(err1, "test precondition (enter works correctly) not met")

        next_state = ChargingStation(vehicle.id, station.id, mock_l2_charger_id())
        err2, sim2 = entity_state_ops.transition_previous_to_next(sim1, env, state, next_state)

        self.assertIsNone(err2, "two subsequent charge instructions should not produce an error")
        self.assertIsNotNone(sim2, "two subsequent charge instructions should update the sim state")

        updated_station = sim2.stations.get(station.id)
        self.assertIsNotNone(updated_station, "station not found in sim")
        dc_available = updated_station.available_chargers.get(mock_dcfc_charger_id())
        l2_available = updated_station.available_chargers.get(mock_l2_charger_id())
        self.assertEqual(dc_available, 1, "should have released DC charger_id on second transition")
        self.assertEqual(l2_available, 0, "second instruction should have claimed the only L2 charger_id")

    ####################################################################################################################
    # ChargingBase #####################################################################################################
    ####################################################################################################################

    def test_charging_base_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingBase, "should be in a charging state")
        self.assertEquals(available_chargers, 0, "should have claimed the only DCFC charger_id")

    def test_charging_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(
            station_id=DefaultIds.mock_station_id(),
            membership=Membership.single_membership("lyft"),
        )
        station = mock_station(membership=base.membership)

        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_charging_base_invalid_charger(self):
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_l2_charger_id()
        vehicle = mock_vehicle(mechatronics=mock_ice())
        sim = mock_sim(
            stations=(station,),
            vehicles=(vehicle,),
            bases=(base,),
        )
        env = mock_env(mechatronics={DefaultIds.mock_mechatronics_ice_id(): mock_ice()})

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.exit(updated_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.available_chargers.get(charger)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingBase, "should still be in a charging state")
        self.assertEquals(available_chargers, 1, "should have returned the only DCFC charger_id")

    def test_charging_base_update(self):
        vehicle = mock_vehicle(soc=0.5)
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_l2_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertAlmostEqual(
            first=updated_vehicle.energy[EnergyType.ELECTRIC],
            second=vehicle.energy[EnergyType.ELECTRIC] + 0.12,
            places=2,
            msg="should have charged for 60 seconds")

    def test_charging_base_update_terminal(self):
        vehicle = mock_vehicle(soc=1.0)
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_base = sim_updated.bases.get(base.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ReserveBase, "vehicle should be in ReserveBase state")
        self.assertEquals(updated_base.available_stalls, 0, "should have taken the only available stall")

    def test_charging_base_enter_with_no_base(self):
        vehicle = mock_vehicle(soc=1.0)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, DefaultIds.mock_base_id(), charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_no_station(self):
        vehicle = mock_vehicle(soc=1.0)
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_missing_station_id(self):
        vehicle = mock_vehicle(soc=1.0)
        base = mock_base()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_no_vehicle(self):
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(DefaultIds.mock_vehicle_id(), base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_subsequent_charge_instructions(self):
        vehicle = mock_vehicle()
        station = mock_station(chargers=immutables.Map({mock_l2_charger_id(): 1, mock_dcfc_charger_id(): 1}))
        base = mock_base(station_id=DefaultIds.mock_station_id())
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(vehicle.id, base.id, mock_dcfc_charger_id())
        err1, sim1 = state.enter(sim, env)
        self.assertIsNone(err1, "test precondition (enter works correctly) not met")

        next_state = ChargingBase(vehicle.id, base.id, mock_l2_charger_id())
        err2, sim2 = entity_state_ops.transition_previous_to_next(sim1, env, state, next_state)

        self.assertIsNone(err2, "two subsequent charge instructions should not produce an error")
        self.assertIsNotNone(sim2, "two subsequent charge instructions should update the sim state")

        updated_station = sim2.stations.get(station.id)
        self.assertIsNotNone(updated_station, "station not found in sim")
        dc_available = updated_station.available_chargers.get(mock_dcfc_charger_id())
        l2_available = updated_station.available_chargers.get(mock_l2_charger_id())
        self.assertEqual(dc_available, 1, "should have released DC charger_id on second transition")
        self.assertEqual(l2_available, 0, "second instruction should have claimed the only L2 charger_id")

    ####################################################################################################################
    # DispatchBase #####################################################################################################
    ####################################################################################################################

    def test_dispatch_base_enter(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase(vehicle.id, base.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchBase, "should be in a dispatch to base state")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(membership=Membership.single_membership("lyft"))

        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase(vehicle.id, base.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_base_exit(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase(vehicle.id, base.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_dispatch_base_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        base = mock_base_from_geoid(geoid=omf_brewing)
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchBase(vehicle.id, base.id, route)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        old_soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(vehicle)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(updated_vehicle)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchBase,
                              "should still be in a dispatch to base state")
        self.assertLess(new_soc, old_soc, "should have less energy")

    def test_dispatch_base_update_terminal(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,)
        )
        env = mock_env()
        route = ()  # empty route should trigger a default transition

        state = DispatchBase(vehicle.id, base.id, route)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_base = sim_updated.bases.get(base.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ReserveBase, "vehicle should be in ReserveBase state")
        self.assertEquals(updated_base.available_stalls, 0, "should have taken the only available stall")

    def test_dispatch_base_enter_no_base(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = DispatchBase(vehicle.id, DefaultIds.mock_base_id(), route)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_base_enter_no_vehicle(self):
        base = mock_base()
        sim = mock_sim(
            bases=(base,),
        )
        env = mock_env()
        route = ()

        state = DispatchBase(DefaultIds.mock_vehicle_id(), base.id, route)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_base_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,),
        )
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, base.geoid)

        state = DispatchBase(vehicle.id, base.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_base_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchBase(vehicle.id, base.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    ####################################################################################################################
    # DispatchStation ##################################################################################################
    ####################################################################################################################

    def test_dispatch_station_enter(self):
        outer_range_brewing = h3.geo_to_h3(39.5892193, -106.1011423, 15)
        vehicle = mock_vehicle()
        station = mock_station_from_geoid(geoid=outer_range_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchStation,
                              "should be in a dispatch to station state")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_station_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        station = mock_station(membership=Membership.single_membership("lyft"))
        charger = mock_dcfc_charger_id()

        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_station_enter_but_already_at_destination(self):
        # vehicle and station have the same geoid
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingStation,
                              "should actually end up charging with no delay since we are already at the destination")

    def test_dispatch_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_dispatch_station_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        station = mock_station_from_geoid(geoid=omf_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        old_soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(vehicle)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(updated_vehicle)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchStation,
                              "should still be in a dispatch to station state")
        self.assertLess(new_soc, old_soc, "should have less energy")

    def test_dispatch_station_update_terminal(self):
        initial_soc = 0.1
        charger = mock_dcfc_charger_id()
        route = ()  # empty route should trigger a default transition
        state = DispatchStation(
            DefaultIds.mock_vehicle_id(),
            DefaultIds.mock_station_id(),
            route,
            charger
        )
        vehicle = mock_vehicle(soc=initial_soc, vehicle_state=state)
        station = mock_station()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()

        # enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        # self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_station = sim_updated.stations.get(station.id)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(updated_vehicle)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingStation,
                              "vehicle should be in ChargingStation state")
        self.assertEquals(updated_station.available_chargers.get(charger), 0,
                          "should have taken the only available charger_id")
        self.assertGreater(new_soc, initial_soc, "should have charged for one time step")

    def test_dispatch_station_enter_no_station(self):
        vehicle = mock_vehicle()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = DispatchStation(vehicle.id, DefaultIds.mock_station_id(), route, charger)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_station_enter_no_vehicle(self):
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            stations=(station,),
        )
        env = mock_env()
        route = ()

        state = DispatchStation(DefaultIds.mock_vehicle_id(), station.id, route, charger)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_station_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        station = mock_station_from_geoid(geoid=omf_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, station.geoid)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_station_enter_route_with_bad_destination(self):
        outer_range_brewing = h3.geo_to_h3(39.5892193, -106.1011423, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        station = mock_station_from_geoid(geoid=omf_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, outer_range_brewing)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim,
                          "invalid route should have not changed sim state - station and route destination do not match")

    ####################################################################################################################
    # DispatchTrip #####################################################################################################
    ####################################################################################################################

    def test_dispatch_trip_enter(self):
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_request = updated_sim.requests.get(request.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchTrip, "should be in a dispatch to request state")
        self.assertEquals(updated_request.dispatched_vehicle, vehicle.id, "request should be assigned this vehicle")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_trip_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        request = mock_request(fleet_id="lyft")

        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_trip_exit(self):
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_dispatch_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=omf_brewing)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchTrip,
                              "should still be in a dispatch to request state")
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )

    def test_dispatch_trip_update_terminal(self):
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = ()  # vehicle is at the request

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_request = sim_updated.requests.get(request.id)
        expected_passengers = board_vehicle(request.passengers, vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ServicingTrip, "vehicle should be in ServicingTrip state")
        self.assertIn(expected_passengers[0], updated_vehicle.vehicle_state.passengers, "passenger not picked up")
        self.assertIsNone(updated_request, "request should no longer exist as it has been picked up")

    def test_dispatch_trip_enter_no_request(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim(vehicles=(vehicle,))  # request not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(updated_sim, "no request at location should result in no update to sim")

    def test_dispatch_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.geoid)

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchTrip(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    ####################################################################################################################
    # Idle #############################################################################################################
    ####################################################################################################################

    def test_idle_enter(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "should be in an idle to request state")

    def test_idle_exit(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_idle_update(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(updated_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "should still be in an Idle state")
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(updated_vehicle.vehicle_state.idle_duration,
                         sim.sim_timestep_duration_seconds,
                         "should have recorded the idle time")

    def test_idle_update_terminal(self):
        initial_soc = 0.0
        ititial_state = DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ())
        vehicle = mock_vehicle(soc=initial_soc).modify_vehicle_state(ititial_state)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(updated_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        is_empty = env.mechatronics.get(updated_vehicle.mechatronics_id).is_empty(updated_vehicle)
        self.assertIsInstance(updated_vehicle.vehicle_state, OutOfService, "vehicle should be OutOfService")
        self.assertTrue(is_empty, "vehicle should have no energy")

    ####################################################################################################################
    # OutOfService #####################################################################################################
    ####################################################################################################################

    def test_out_of_service_enter(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService(vehicle.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, OutOfService, "should be in an OutOfService state")

    def test_out_of_service_exit(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_out_of_service_update(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, updated_sim = state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, OutOfService, "should still be in an OutOfService state")
        self.assertEqual(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have the same energy",
        )

    # def test_out_of_service_update_terminal(self):  # there is no terminal state for OutOfService

    ####################################################################################################################
    # Repositioning ####################################################################################################
    ####################################################################################################################

    def test_repositioning_enter(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, vehicle.geoid)

        state = Repositioning(vehicle.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Repositioning, "should be in a repositioning state")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_repositioning_exit(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, vehicle.geoid)

        state = Repositioning(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEquals(entered_sim, exited_sim, "should see no change due to exit")

    def test_repositioning_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = Repositioning(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, Repositioning, "should still be in a Repositioning state")
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )

    def test_repositioning_update_terminal(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = Repositioning(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertIsNotNone(entered_sim, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "vehicle should be in Idle state")

    def test_repositioning_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = ()

        state = Repositioning(vehicle.id, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_repositioning_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, vehicle.geoid)

        state = Repositioning(vehicle.id, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state") \
 \
            ####################################################################################################################

    # ReserveBase ######################################################################################################
    ####################################################################################################################

    def test_reserve_base_enter(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase(vehicle.id, base.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_base = updated_sim.bases.get(base.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ReserveBase, "should be in an ReserveBase state")
        self.assertEqual(updated_base.available_stalls, 0, "only stall should now be occupied")

    def test_reserve_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(membership=Membership.single_membership("lyft"))

        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase(vehicle.id, base.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_reserve_base_exit(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        entered_base = entered_sim.bases.get(base.id)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertEqual(entered_base.available_stalls, 0, "test precondition (stall in use) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        exited_base = exited_sim.bases.get(base.id)
        self.assertIsNone(error, "should have no errors")
        self.assertEqual(exited_base.available_stalls, 1, "should have released stall")

    def test_reserve_base_update(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, updated_sim = state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, ReserveBase, "should still be in a ReserveBase state")
        self.assertEqual(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have the same energy",
        )

    def test_reserve_base_enter_no_base(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = ReserveBase(vehicle.id, DefaultIds.mock_base_id())
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_reserve_base_enter_no_vehicle(self):
        base = mock_base()
        sim = mock_sim(
            bases=(base,),
        )
        env = mock_env()
        route = ()

        state = ReserveBase(DefaultIds.mock_vehicle_id(), base.id)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_reserve_base_no_stalls_available(self):
        vehicle = mock_vehicle()
        base = mock_base(stall_count=0)
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "no stall failure should not result in an exception (fail silently)")
        self.assertIsNone(entered_sim, "no stall failure should result in no SimulationState result")

    # def test_reserve_base_update_terminal(self):  # there is no terminal state for OutOfService

    ####################################################################################################################
    # ServicingTrip ####################################################################################################
    ####################################################################################################################

    def test_servicing_trip_enter(self):
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ServicingTrip, "should be in a ServicingTrip state")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_servicing_trip_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        request = mock_request(fleet_id="lyft")

        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_servicing_trip_exit(self):
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(destination=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")  # errors due to passengers not being at destination

    def test_servicing_trip_exit_when_still_has_passengers(self):
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids()
        self.assertNotEqual(request.origin, request.destination, "test invariant failed")
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)

        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")  # errors due to passengers not being at destination
        self.assertIsNone(exited_sim, "should not have allowed exit of ServicingTrip")

    def test_servicing_trip_exit_when_still_has_passengers_but_out_of_fuel(self):
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(soc=0, vehicle_state=prev_state)
        request = mock_request_from_geoids()
        self.assertNotEqual(request.origin, request.destination, "test invariant failed")
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)

        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")  # errors due to passengers not being at destination
        self.assertIsNotNone(exited_sim,
                             "should have allowed exit of ServicingTrip because out of fuel allows transition to OutOfService")

    def test_servicing_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle_from_geoid(geoid=near, vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=near, destination=omf_brewing)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, sim_servicing = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_servicing, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, ServicingTrip, "should still be in a servicing state")
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(updated_vehicle.vehicle_state.passengers, request.passengers, "should have passengers")

    def test_servicing_trip_update_terminal(self):
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid, destination=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = ()  # end of route

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, sim_servicing = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_servicing, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "vehicle should be in Idle state")

    def test_servicing_trip_enter_no_request(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim(vehicles=(vehicle,))  # request not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(updated_sim, "no request at location should result in no update to sim")

    def test_servicing_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=vehicle.geoid)
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(request.geoid, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_servicing_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.destination)

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_servicing_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip(DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ())
        vehicle = mock_vehicle_from_geoid(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)  # request.destination should not be omf brewing co

        state = ServicingTrip(vehicle.id, request.id, sim.sim_time, route, request.passengers)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    ####################################################################################################################
    # ChargeQueueing ###################################################################################################
    ####################################################################################################################

    def test_charge_queueing_enter(self):
        vehicle = mock_vehicle_from_geoid()
        station = mock_station_from_geoid(chargers={})
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing(vehicle.id, station.id, mock_dcfc_charger_id(), 0)
        error, updated_sim = state.enter(sim, env)

        updated_station = updated_sim.stations.get(station.id)
        enqueued_count = updated_station.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())

        self.assertIsNone(error, "should have no errors")
        self.assertIsNotNone(updated_sim, "the sim should have been updated")
        self.assertEqual(enqueued_count, 1, "the station should also know 1 new vehicle is enqueued")

    def test_charge_queueing_exit(self):
        vehicle = mock_vehicle_from_geoid()
        station = mock_station_from_geoid(chargers={})
        sim0 = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing(vehicle.id, station.id, mock_dcfc_charger_id(), 0)
        err1, sim1 = state.enter(sim0, env)

        self.assertIsNone(err1, "test invariant failed")
        self.assertIsNotNone(sim1, "test invariant failed")

        err2, sim2 = state.exit(sim1, env)

        updated_station = sim2.stations.get(station.id)
        enqueued_count = updated_station.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())

        self.assertIsNone(err2, "there should be no error")
        self.assertIsNotNone(sim2, "exit should have succeeded")
        self.assertEqual(enqueued_count, 0, "the station should also know the vehicle was dequeued")

    def test_charge_queueing_update(self):
        vehicle_charging = mock_vehicle_from_geoid(vehicle_id="charging")
        vehicle_queueing = mock_vehicle_from_geoid(vehicle_id="queueing")
        station = mock_station_from_geoid()
        sim0 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,), stations=(station,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, mock_dcfc_charger_id())
        e1, sim1 = charging_state.enter(sim0, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, mock_dcfc_charger_id(), 0)
        e2, sim2 = state.enter(sim1, env)

        self.assertIsNone(e2, "test invariant failed")
        self.assertIsNotNone(sim2, "test invariant failed")

        e3, sim3 = state.update(sim2, env)

        self.assertIsNone(e3, "should have no errors")
        self.assertIsNotNone(sim3, "should have updated the sim")

        updated_vehicle = sim3.vehicles.get(vehicle_queueing.id)
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle_queueing.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )

        # update should apply idle cost if stall is still not available

    def test_charge_queueing_update_terminal(self):
        vehicle_charging = mock_vehicle_from_geoid()
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,), stations=(station,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, mock_dcfc_charger_id())
        e1, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, mock_dcfc_charger_id(), 0)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")

        # should have removed self from queue and moved to ChargingStation if available
        #  otherwise, never ends

    def test_charge_queueing_enter_no_vehicle(self):
        station = mock_station_from_geoid()
        sim = mock_sim(stations=(station,))
        env = mock_env()

        state = ChargeQueueing(DefaultIds.mock_vehicle_id(), station.id, mock_dcfc_charger_id(), 0)
        err, _ = state.enter(sim, env)

        self.assertIsInstance(err, Exception, "should have exception")

    def test_charge_queueing_enter_when_station_has_charger_available(self):
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_queueing,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing(vehicle_queueing.id, station.id, mock_dcfc_charger_id(), 0)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(updated_sim, "should not have entered a queueing state")
