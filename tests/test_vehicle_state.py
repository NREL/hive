from dataclasses import replace
from unittest import TestCase

import immutables
import h3

from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.model.membership import Membership
from nrel.hive.model.sim_time import SimTime
from nrel.hive.model.vehicle.trip_phase import TripPhase
from nrel.hive.resources.mock_lobster import (
    DefaultIds,
    mock_base,
    mock_base_from_geoid,
    mock_dcfc_charger_id,
    mock_env,
    mock_ice,
    mock_l2_charger_id,
    mock_request,
    mock_request_from_geoids,
    mock_route_from_geoids,
    mock_sim,
    mock_station,
    mock_station_from_geoid,
    mock_vehicle,
    mock_vehicle_from_geoid,
)
from nrel.hive.state.entity_state import entity_state_ops
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.vehicle_state.charge_queueing import ChargeQueueing
from nrel.hive.state.vehicle_state.charging_base import ChargingBase
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.state.vehicle_state.dispatch_base import DispatchBase
from nrel.hive.state.vehicle_state.dispatch_pooling_trip import DispatchPoolingTrip
from nrel.hive.state.vehicle_state.dispatch_station import DispatchStation
from nrel.hive.state.vehicle_state.dispatch_trip import DispatchTrip
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.repositioning import Repositioning
from nrel.hive.state.vehicle_state.reserve_base import ReserveBase
from nrel.hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from nrel.hive.state.vehicle_state.servicing_trip import ServicingTrip
from nrel.hive.state.vehicle_state.out_of_service import OutOfService


class TestVehicleState(TestCase):
    def test_charging_station_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.get_available_chargers(charger)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingStation,
            "should be in a charging state",
        )
        self.assertEqual(
            available_chargers,
            0,
            "should have claimed the only DCFC charger_id",
        )

    def test_charging_station_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        station = mock_station(membership=Membership.single_membership("lyft"))

        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, mock_dcfc_charger_id())
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should return none for updated sim")

    def test_charging_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, charger)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.exit(Idle.build(vehicle.id), updated_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.get_available_chargers(charger)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingStation,
            "should still be in a charging state",
        )
        self.assertEqual(
            available_chargers,
            1,
            "should have returned the only DCFC charger_id",
        )

    def test_charging_station_update(self):
        vehicle = mock_vehicle(soc=0.5)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        entered_state = sim_with_charging_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertAlmostEqual(
            first=updated_vehicle.energy[EnergyType.ELECTRIC],
            second=vehicle.energy[EnergyType.ELECTRIC] + 0.76,
            places=2,
            msg="should have charged for 60 seconds",
        )

        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_charging_station_update_terminal(self):
        vehicle = mock_vehicle(soc=1)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_station = sim_updated.stations.get(station.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Idle,
            "vehicle should be in idle state",
        )
        self.assertEqual(
            updated_station.get_available_chargers(charger),
            1,
            "should have returned the charger_id",
        )

    def test_charging_station_enter_with_no_station(self):
        vehicle = mock_vehicle(soc=0.99)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()

        state = ChargingStation.build(vehicle.id, DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_enter_with_no_vehicle(self):
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            stations=(station,),
        )
        env = mock_env()

        state = ChargingStation.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_station_id(), charger
        )
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

        state = ChargingStation.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_station_id(), charger
        )
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_subsequent_charge_instructions(self):
        vehicle = mock_vehicle()
        station = mock_station(
            chargers=immutables.Map({mock_l2_charger_id(): 1, mock_dcfc_charger_id(): 1})
        )
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargingStation.build(vehicle.id, station.id, mock_dcfc_charger_id())
        err1, sim1 = state.enter(sim, env)
        entered_state = sim1.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(err1, "test precondition (enter works correctly) not met")

        next_state = ChargingStation.build(vehicle.id, station.id, mock_l2_charger_id())
        err2, sim2 = entity_state_ops.transition_previous_to_next(sim1, env, state, next_state)
        next_entered_state = sim2.vehicles.get(vehicle.id).vehicle_state

        self.assertIsNone(
            err2,
            "two subsequent charge instructions should not produce an error",
        )
        self.assertIsNotNone(
            sim2,
            "two subsequent charge instructions should update the sim state",
        )
        self.assertNotEqual(
            entered_state.instance_id,
            next_entered_state.instance_id,
            "should have different instance ids",
        )

        updated_station = sim2.stations.get(station.id)
        self.assertIsNotNone(updated_station, "station not found in sim")
        dc_available = updated_station.get_available_chargers(mock_dcfc_charger_id())
        l2_available = updated_station.get_available_chargers(mock_l2_charger_id())
        self.assertEqual(
            dc_available,
            1,
            "should have released DC charger_id on second transition",
        )
        self.assertEqual(
            l2_available,
            0,
            "second instruction should have claimed the only L2 charger_id",
        )

    def test_charging_base_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.get_available_chargers(charger)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingBase,
            "should be in a charging state",
        )
        self.assertEqual(
            available_chargers,
            0,
            "should have claimed the only DCFC charger_id",
        )

    def test_charging_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(
            station_id=DefaultIds.mock_station_id(),
            membership=Membership.single_membership("lyft"),
        )
        station = mock_station(membership=base.membership)

        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
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

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.exit(Idle.build(vehicle.id), updated_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_station = updated_sim.stations.get(station.id)
        available_chargers = updated_station.get_available_chargers(charger)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingBase,
            "should still be in a charging state",
        )
        self.assertEqual(
            available_chargers,
            1,
            "should have returned the only DCFC charger_id",
        )

    def test_charging_base_update(self):
        vehicle = mock_vehicle(soc=0.5)
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_l2_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        entered_state = sim_with_charging_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertAlmostEqual(
            first=updated_vehicle.energy[EnergyType.ELECTRIC],
            second=vehicle.energy[EnergyType.ELECTRIC] + 0.12,
            places=2,
            msg="should have charged for 60 seconds",
        )

        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_charging_base_update_terminal(self):
        vehicle = mock_vehicle(soc=1.0)
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_charging_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_base = sim_updated.bases.get(base.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ReserveBase,
            "vehicle should be in ReserveBase state",
        )
        self.assertEqual(
            updated_base.available_stalls,
            0,
            "should have taken the only available stall",
        )

    def test_charging_base_enter_with_no_base(self):
        vehicle = mock_vehicle(soc=1.0)
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()

        state = ChargingBase.build(vehicle.id, DefaultIds.mock_base_id(), charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_no_station(self):
        vehicle = mock_vehicle(soc=1.0)
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_missing_station_id(self):
        vehicle = mock_vehicle(soc=1.0)
        base = mock_base()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, charger)
        enter_error, _ = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_enter_with_no_vehicle(self):
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = mock_dcfc_charger_id()
        sim = mock_sim(stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(DefaultIds.mock_vehicle_id(), base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_base_subsequent_charge_instructions(self):
        vehicle = mock_vehicle()
        station = mock_station(
            chargers=immutables.Map({mock_l2_charger_id(): 1, mock_dcfc_charger_id(): 1})
        )
        base = mock_base(station_id=DefaultIds.mock_station_id())
        sim = mock_sim(vehicles=(vehicle,), stations=(station,), bases=(base,))
        env = mock_env()

        state = ChargingBase.build(vehicle.id, base.id, mock_dcfc_charger_id())
        err1, sim1 = state.enter(sim, env)
        self.assertIsNone(err1, "test precondition (enter works correctly) not met")

        next_state = ChargingBase.build(vehicle.id, base.id, mock_l2_charger_id())
        err2, sim2 = entity_state_ops.transition_previous_to_next(sim1, env, state, next_state)

        self.assertIsNone(
            err2,
            "two subsequent charge instructions should not produce an error",
        )
        self.assertIsNotNone(
            sim2,
            "two subsequent charge instructions should update the sim state",
        )

        updated_station = sim2.stations.get(station.id)
        self.assertIsNotNone(updated_station, "station not found in sim")
        dc_available = updated_station.get_available_chargers(mock_dcfc_charger_id())
        l2_available = updated_station.get_available_chargers(mock_l2_charger_id())
        self.assertEqual(
            dc_available,
            1,
            "should have released DC charger_id on second transition",
        )
        self.assertEqual(
            l2_available,
            0,
            "second instruction should have claimed the only L2 charger_id",
        )

    def test_dispatch_base_enter(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase.build(vehicle.id, base.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchBase,
            "should be in a dispatch to base state",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(membership=Membership.single_membership("lyft"))

        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase.build(vehicle.id, base.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_base_exit(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, base.geoid)

        state = DispatchBase.build(vehicle.id, base.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEqual(entered_sim, exited_sim, "should see no change due to exit")

    def test_dispatch_base_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        base = mock_base_from_geoid(geoid=omf_brewing)
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchBase.build(vehicle.id, base.id, route)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        entered_state = sim_with_dispatched_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        old_soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(vehicle)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(
            updated_vehicle
        )
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchBase,
            "should still be in a dispatch to base state",
        )
        self.assertLess(new_soc, old_soc, "should have less energy")

        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_dispatch_base_update_terminal(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()
        route = ()  # empty route should trigger a default transition

        state = DispatchBase.build(vehicle.id, base.id, route)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_base = sim_updated.bases.get(base.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ReserveBase,
            "vehicle should be in ReserveBase state",
        )
        self.assertEqual(
            updated_base.available_stalls,
            0,
            "should have taken the only available stall",
        )

    def test_dispatch_base_enter_no_base(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = DispatchBase.build(vehicle.id, DefaultIds.mock_base_id(), route)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_base_enter_no_vehicle(self):
        base = mock_base()
        sim = mock_sim(
            bases=(base,),
        )
        env = mock_env()
        route = ()

        state = DispatchBase.build(DefaultIds.mock_vehicle_id(), base.id, route)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_base_enter_route_with_bad_source(self):
        # omf brewing is not the same location as the vehicle
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,),
        )
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, base.geoid)

        state = DispatchBase.build(vehicle.id, base.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_base_enter_route_with_bad_destination(self):
        # omf brewing is not the same location as the base
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(
            vehicles=(vehicle,),
            bases=(base,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchBase.build(vehicle.id, base.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_station_enter(self):
        outer_range_brewing = h3.geo_to_h3(39.5892193, -106.1011423, 15)
        vehicle = mock_vehicle()
        station = mock_station_from_geoid(geoid=outer_range_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchStation,
            "should be in a dispatch to station state",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

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

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_station_enter_but_already_at_destination(self):
        # vehicle and station have the same geoid
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingStation,
            "should actually end up charging with no delay since we are already at the destination",
        )

    def test_dispatch_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, station.geoid)

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEqual(entered_sim, exited_sim, "should see no change due to exit")

    def test_dispatch_station_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        station = mock_station_from_geoid(geoid=omf_brewing)
        charger = mock_dcfc_charger_id()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        entered_state = sim_with_dispatched_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        old_soc = env.mechatronics.get(vehicle.mechatronics_id).fuel_source_soc(vehicle)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(
            updated_vehicle
        )
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchStation,
            "should still be in a dispatch to station state",
        )
        self.assertLess(new_soc, old_soc, "should have less energy")

        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_dispatch_station_update_terminal(self):
        initial_soc = 0.1
        charger = mock_dcfc_charger_id()
        route = ()  # empty route should trigger a default transition
        state = DispatchStation.build(
            DefaultIds.mock_vehicle_id(),
            DefaultIds.mock_station_id(),
            route,
            charger,
        )
        vehicle = mock_vehicle(soc=initial_soc, vehicle_state=state)
        station = mock_station()
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        # enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        # self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_station = sim_updated.stations.get(station.id)
        new_soc = env.mechatronics.get(updated_vehicle.mechatronics_id).fuel_source_soc(
            updated_vehicle
        )
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ChargingStation,
            "vehicle should be in ChargingStation state",
        )
        self.assertEqual(
            updated_station.get_available_chargers(charger),
            0,
            "should have taken the only available charger_id",
        )
        self.assertGreater(new_soc, initial_soc, "should have charged for one time step")

    def test_dispatch_station_enter_no_station(self):
        vehicle = mock_vehicle()
        charger = mock_dcfc_charger_id()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = DispatchStation.build(vehicle.id, DefaultIds.mock_station_id(), route, charger)
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

        state = DispatchStation.build(DefaultIds.mock_vehicle_id(), station.id, route, charger)
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

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
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

        state = DispatchStation.build(vehicle.id, station.id, route, charger)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(
            enter_sim,
            "invalid route should have not changed sim state"
            " - station and route destination do not match",
        )

    def test_dispatch_trip_enter(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_request = updated_sim.requests.get(request.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchTrip,
            "should be in a dispatch to request state",
        )
        self.assertEqual(
            updated_request.dispatched_vehicle,
            vehicle.id,
            "request should be assigned this vehicle",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_trip_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        request = mock_request(fleet_id="lyft")

        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_trip_exit(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertTrue(
            entered_sim.requests.get(request.id).dispatched_vehicle == vehicle.id,
            "test precondition not met",
        )

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(
            exited_sim.requests.get(request.id).dispatched_vehicle,
            "should have unset the dispatched vehicle",
        )

    def test_dispatch_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=omf_brewing)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        entered_state = sim_with_dispatched_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchTrip,
            "should still be in a dispatch to request state",
        )
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_dispatch_trip_update_terminal(self):
        vehicle = mock_vehicle_from_geoid(geoid="8f268cdac30e2d3")
        request = replace(
            mock_request_from_geoids(
                origin="8f268cdac30e2d3",
                destination="8f268cdac70e2d3",
            ),
            dispatched_vehicle=vehicle.id,
            dispatched_vehicle_time=mock_sim().sim_time,
        )
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = ()  # vehicle is at the request

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_request = sim_updated.requests.get(request.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ServicingTrip,
            "vehicle should be in ServicingTrip state",
        )
        self.assertEqual(
            request,
            updated_vehicle.vehicle_state.request,
            "passengers not picked up",
        )
        self.assertIsNone(
            updated_request,
            "request should no longer exist as it has been picked up",
        )

    def test_dispatch_trip_enter_no_request(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim(vehicles=(vehicle,))  # request not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(
            updated_sim,
            "no request at location should result in no update to sim",
        )

    def test_dispatch_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_idle_enter(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase.build(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ())
        )
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle.build(vehicle.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Idle,
            "should be in an idle to request state",
        )

    def test_idle_exit(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase.build(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ())
        )
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle.build(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEqual(entered_sim, exited_sim, "should see no change due to exit")

    def test_idle_update(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_vehicle_state(
            DispatchBase.build(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ())
        )
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle.build(vehicle.id)
        enter_error, updated_sim = state.enter(sim, env)
        entered_state = updated_sim.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(updated_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Idle,
            "should still be in an Idle state",
        )
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            updated_vehicle.vehicle_state.idle_duration,
            sim.sim_timestep_duration_seconds,
            "should have recorded the idle time",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_idle_update_terminal(self):
        initial_soc = 0.0
        ititial_state = DispatchBase.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()
        )
        vehicle = mock_vehicle(soc=initial_soc).modify_vehicle_state(ititial_state)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle.build(vehicle.id)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(updated_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        is_empty = env.mechatronics.get(updated_vehicle.mechatronics_id).is_empty(updated_vehicle)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            OutOfService,
            "vehicle should be OutOfService",
        )
        self.assertTrue(is_empty, "vehicle should have no energy")

    def test_out_of_service_enter(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService.build(vehicle.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            OutOfService,
            "should be in an OutOfService state",
        )

    def test_out_of_service_exit(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService.build(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEqual(entered_sim, exited_sim, "should see no change due to exit")

    def test_out_of_service_update(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle(soc=0.0)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = OutOfService.build(vehicle.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, updated_sim = state.update(entered_sim, env)
        entered_state = updated_sim.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            OutOfService,
            "should still be in an OutOfService state",
        )
        self.assertEqual(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have the same energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    # def test_out_of_service_update_terminal(self):  # there is no terminal state for OutOfService

    def test_repositioning_enter(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, vehicle.geoid)

        state = Repositioning.build(vehicle.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Repositioning,
            "should be in a repositioning state",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_repositioning_exit(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, vehicle.geoid)

        state = Repositioning.build(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertEqual(entered_sim, exited_sim, "should see no change due to exit")

    def test_repositioning_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = Repositioning.build(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        entered_state = entered_sim.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Repositioning,
            "should still be in a Repositioning state",
        )
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_repositioning_update_terminal(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()
        route = ()

        state = Repositioning.build(vehicle.id, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertIsNotNone(entered_sim, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(entered_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Idle,
            "vehicle should be in Idle state",
        )

    def test_repositioning_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = ()

        state = Repositioning.build(vehicle.id, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_repositioning_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, vehicle.geoid)

        state = Repositioning.build(vehicle.id, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_reserve_base_enter(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase.build(vehicle.id, base.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_base = updated_sim.bases.get(base.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ReserveBase,
            "should be in an ReserveBase state",
        )
        self.assertEqual(
            updated_base.available_stalls,
            0,
            "only stall should now be occupied",
        )

    def test_reserve_base_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        base = mock_base(membership=Membership.single_membership("lyft"))

        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase.build(vehicle.id, base.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_reserve_base_exit(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase.build(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        entered_base = entered_sim.bases.get(base.id)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertEqual(
            entered_base.available_stalls,
            0,
            "test precondition (stall in use) not met",
        )

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        exited_base = exited_sim.bases.get(base.id)
        self.assertIsNone(error, "should have no errors")
        self.assertEqual(exited_base.available_stalls, 1, "should have released stall")

    def test_reserve_base_update(self):
        vehicle = mock_vehicle()
        base = mock_base()
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase.build(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, updated_sim = state.update(entered_sim, env)
        entered_state = updated_sim.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertEqual(vehicle.geoid, updated_vehicle.geoid, "should not have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ReserveBase,
            "should still be in a ReserveBase state",
        )
        self.assertEqual(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have the same energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_reserve_base_enter_no_base(self):
        vehicle = mock_vehicle()
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()

        state = ReserveBase.build(vehicle.id, DefaultIds.mock_base_id())
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_reserve_base_enter_no_vehicle(self):
        base = mock_base()
        sim = mock_sim(
            bases=(base,),
        )
        env = mock_env()

        state = ReserveBase.build(DefaultIds.mock_vehicle_id(), base.id)
        enter_error, _ = state.enter(sim, env)
        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_reserve_base_no_stalls_available(self):
        vehicle = mock_vehicle()
        base = mock_base(stall_count=0)
        sim = mock_sim(vehicles=(vehicle,), bases=(base,))
        env = mock_env()

        state = ReserveBase.build(vehicle.id, base.id)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(
            enter_error,
            "no stall failure should not result in an exception (fail silently)",
        )
        self.assertIsNone(
            entered_sim,
            "no stall failure should result in no SimulationState result",
        )

    def test_servicing_trip_enter(self):
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ServicingTrip,
            "should be in a ServicingTrip state",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_servicing_trip_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        request = mock_request(fleet_id="lyft")

        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_servicing_trip_exit(self):
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(destination=vehicle.geoid)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(
            error, "should have no errors"
        )  # errors due to passengers not being at destination

    def test_servicing_trip_exit_when_still_has_passengers(self):
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids()
        self.assertNotEqual(request.origin, request.destination, "test invariant failed")
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()

        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(
            error, "should have no errors"
        )  # errors due to passengers not being at destination
        self.assertIsNone(exited_sim, "should not have allowed exit of ServicingTrip")

    def test_servicing_trip_exit_when_still_has_passengers_but_out_of_fuel(
        self,
    ):
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(soc=0, vehicle_state=prev_state)
        request = mock_request_from_geoids()
        self.assertNotEqual(request.origin, request.destination, "test invariant failed")
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()

        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, updated_sim = state.update(entered_sim, env)

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsNone(
            error, "should have no errors"
        )  # errors due to passengers not being at destination
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            OutOfService,
            "vehicle should be out of service",
        )

    def test_servicing_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle_from_geoid(geoid=near, vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=near, destination=omf_brewing)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, sim_servicing = state.enter(sim, env)
        entered_state = sim_servicing.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(sim_servicing, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ServicingTrip,
            "should still be in a servicing state",
        )
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            updated_vehicle.vehicle_state.request,
            request,
            "should have passengers",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_servicing_trip_update_terminal(self):
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid, destination=vehicle.geoid)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = ()  # end of route

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, sim_servicing = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_servicing, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            Idle,
            "vehicle should be in Idle state",
        )

    def test_servicing_trip_enter_no_request(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim_with_req = simulation_state_ops.add_request_safe(
            mock_sim(vehicles=(vehicle,)), request
        ).unwrap()

        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        rev_route = mock_route_from_geoids(request.geoid, vehicle.geoid)

        vs0 = DispatchTrip.build(vehicle.id, request.id, route)
        e2, s0 = vs0.enter(sim_with_req, env)
        self.assertIsNone(e2, "test invariant failed")

        # begin test
        e1, sim_no_req = simulation_state_ops.remove_request(s0, request.id)
        vs1 = ServicingTrip.build(vehicle.id, request, sim_no_req.sim_time, rev_route)
        e3, s1 = vs1.enter(sim_no_req, env)

        self.assertIsNone(e3, "should have no errors")
        self.assertIsNone(s1, "no request at location should result in no update to sim")

    def test_servicing_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=vehicle.geoid)
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(request.geoid, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_servicing_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle(vehicle_state=prev_state)
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.destination)

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNotNone(enter_error, "an invalid route should return an error")

    def test_servicing_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        prev_state = DispatchTrip.build(
            DefaultIds.mock_vehicle_id(), DefaultIds.mock_request_id(), ()
        )
        vehicle = mock_vehicle_from_geoid(vehicle_state=prev_state)
        request = mock_request_from_geoids(origin=vehicle.geoid)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(
            vehicle.geoid, omf_brewing
        )  # request.destination should not be omf brewing co

        state = ServicingTrip.build(vehicle.id, request, sim.sim_time, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNotNone(enter_error, "bad destination is a good reason to bork this sim")

    def test_charge_queueing_enter(self):
        vehicle = mock_vehicle()
        s0 = mock_station()
        err, station = s0.checkout_charger(mock_dcfc_charger_id())
        self.assertIsNone(
            err,
            "test invariant failed (station should have charger checked out)",
        )
        sim = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing.build(vehicle.id, station.id, mock_dcfc_charger_id(), 0)
        error, updated_sim = state.enter(sim, env)
        self.assertIsNone(error, "error when vehicle entered queueing state")
        self.assertIsNotNone(updated_sim, "proposed vehicle state couldn't be entered")

        updated_station = updated_sim.stations.get(station.id)
        enqueued_count = updated_station.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())

        self.assertIsNone(error, "should have no errors")
        self.assertIsNotNone(updated_sim, "the sim should have been updated")
        self.assertEqual(
            enqueued_count,
            1,
            "the station should also know 1 new vehicle is enqueued",
        )

    def test_charge_queueing_exit(self):
        vehicle = mock_vehicle()
        s0 = mock_station()
        err, station = s0.checkout_charger(mock_dcfc_charger_id())
        self.assertIsNone(
            err,
            "test invariant failed (station should have charger checked out)",
        )
        sim0 = mock_sim(vehicles=(vehicle,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing.build(vehicle.id, station.id, mock_dcfc_charger_id(), 0)
        err1, sim1 = state.enter(sim0, env)

        self.assertIsNone(err1, "test invariant failed")
        self.assertIsNotNone(sim1, "test invariant failed")

        err2, sim2 = state.exit(Idle.build(vehicle.id), sim1, env)

        updated_station = sim2.stations.get(station.id)
        enqueued_count = updated_station.enqueued_vehicle_count_for_charger(mock_dcfc_charger_id())

        self.assertIsNone(err2, "there should be no error")
        self.assertIsNotNone(sim2, "exit should have succeeded")
        self.assertEqual(
            enqueued_count,
            0,
            "the station should also know the vehicle was dequeued",
        )

    def test_charge_queueing_update(self):
        vehicle_charging = mock_vehicle_from_geoid(vehicle_id="charging")
        vehicle_queueing = mock_vehicle_from_geoid(vehicle_id="queueing")
        station = mock_station_from_geoid()
        sim0 = mock_sim(
            vehicles=(
                vehicle_charging,
                vehicle_queueing,
            ),
            stations=(station,),
        )
        env = mock_env()

        charging_state = ChargingStation.build(
            vehicle_charging.id, station.id, mock_dcfc_charger_id()
        )
        e1, sim1 = charging_state.enter(sim0, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing.build(vehicle_queueing.id, station.id, mock_dcfc_charger_id(), 0)
        e2, sim2 = state.enter(sim1, env)
        entered_state = sim2.vehicles.get(vehicle_queueing.id).vehicle_state

        self.assertIsNone(e2, "test invariant failed")
        self.assertIsNotNone(sim2, "test invariant failed")

        e3, sim3 = entered_state.update(sim2, env)

        self.assertIsNone(e3, "should have no errors")
        self.assertIsNotNone(sim3, "should have updated the sim")

        updated_vehicle = sim3.vehicles.get(vehicle_queueing.id)
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle_queueing.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

        # update should apply idle cost if stall is still not available

    def test_charge_queueing_update_terminal(self):
        v_charging = mock_vehicle_from_geoid(vehicle_id="charging", soc=0.2)
        v_queueing = mock_vehicle_from_geoid(vehicle_id="queueing")
        charger_id = mock_dcfc_charger_id()
        station = mock_station(chargers={charger_id: 1})
        sim0 = mock_sim(
            vehicles=(
                v_charging,
                v_queueing,
            ),
            stations=(station,),
        )
        env = mock_env()

        charging_state = ChargingStation.build(v_charging.id, station.id, charger_id)
        e1, sim1 = charging_state.enter(sim0, env)
        e2, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")
        self.assertIsNone(e2, "test invariant failed")

        state = ChargeQueueing.build(v_queueing.id, station.id, charger_id, 0)
        error, sim3 = state.enter(sim2, env)

        self.assertIsNone(error, "should have no errors")
        s_updated = sim3.stations.get(station.id)
        v_q_updated = sim3.vehicles.get(v_queueing.id)
        enqueued = s_updated.enqueued_vehicle_count_for_charger(charger_id)
        self.assertIsNotNone(s_updated, "station should be in simulation")
        self.assertIsNotNone(v_q_updated, "vehicle should be in simulation")
        self.assertIsInstance(v_q_updated.vehicle_state, ChargeQueueing, "should be enqueued")
        self.assertEqual(enqueued, 1, "should have one enqueued vehicle")

        # should have removed self from queue and moved to ChargingStation if available
        #  otherwise, never ends

    def test_charge_queueing_enter_no_vehicle(self):
        station = mock_station_from_geoid()
        sim = mock_sim(stations=(station,))
        env = mock_env()

        state = ChargeQueueing.build(
            DefaultIds.mock_vehicle_id(), station.id, mock_dcfc_charger_id(), 0
        )
        err, _ = state.enter(sim, env)

        self.assertIsInstance(err, Exception, "should have exception")

    def test_charge_queueing_enter_when_station_has_charger_available(self):
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_queueing,), stations=(station,))
        env = mock_env()

        state = ChargeQueueing.build(vehicle_queueing.id, station.id, mock_dcfc_charger_id(), 0)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(updated_sim, "should not have entered a queueing state")

    def test_dispatch_pooling_trip_enter(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_request = updated_sim.requests.get(request.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchPoolingTrip,
            "should be in a dispatch to request state",
        )
        self.assertEqual(
            updated_request.dispatched_vehicle,
            vehicle.id,
            "request should be assigned this vehicle",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_pooling_trip_enter_two_requests(self):
        vehicle = mock_vehicle()
        r1 = mock_request("r1", 39.70, -104.97, 39.85, -104.97)  # pickup 1, dropoff 2
        r2 = mock_request("r2", 39.75, -104.97, 39.80, -104.97)  # pickup 2, dropoff 1
        s0 = mock_sim(vehicles=(vehicle,))
        env = mock_env()
        s1 = simulation_state_ops.add_request_safe(s0, r1).unwrap()
        s2 = simulation_state_ops.add_request_safe(s1, r2).unwrap()

        route = mock_route_from_geoids(vehicle.geoid, r1.geoid)
        trip_plan = (
            (r1.id, TripPhase.PICKUP),
            (r2.id, TripPhase.PICKUP),
            (r2.id, TripPhase.DROPOFF),
            (r1.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        error, updated_sim = state.enter(s2, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_r1 = updated_sim.requests.get(r1.id)
        updated_r2 = updated_sim.requests.get(r2.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchPoolingTrip,
            "should be in a dispatch to request state",
        )
        self.assertEqual(
            updated_r1.dispatched_vehicle,
            vehicle.id,
            "r1 should be assigned this vehicle",
        )
        self.assertEqual(
            updated_r2.dispatched_vehicle,
            vehicle.id,
            "r2 should be assigned this vehicle",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_dispatch_pooling_trip_bad_membership(self):
        vehicle = mock_vehicle(membership=Membership.single_membership("uber"))
        request = mock_request(fleet_id="lyft")
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(updated_sim, "should have returned None for updated_sim")

    def test_dispatch_pooling_trip_exit(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")
        self.assertTrue(
            entered_sim.requests.get(request.id).dispatched_vehicle == vehicle.id,
            "test precondition not met",
        )

        # begin test
        error, exited_sim = state.exit(Idle.build(vehicle.id), entered_sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(
            exited_sim.requests.get(request.id).dispatched_vehicle,
            "should have unset the dispatched vehicle",
        )

    def test_dispatch_pooling_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        far = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        request = mock_request_from_geoids(origin=far)
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(near, far)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        enter_error, sim_with_dispatched_vehicle = state.enter(sim, env)
        entered_state = sim_with_dispatched_vehicle.vehicles.get(vehicle.id).vehicle_state
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = entered_state.update(sim_with_dispatched_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchPoolingTrip,
            "should still be in a dispatch to request state",
        )
        self.assertLess(
            updated_vehicle.energy[EnergyType.ELECTRIC],
            vehicle.energy[EnergyType.ELECTRIC],
            "should have less energy",
        )
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_dispatch_pooling_trip_update_terminal(self):
        vehicle = mock_vehicle_from_geoid(geoid="8f268cdac30e2d3")
        request = mock_request_from_geoids(origin="8f268cdac30e2d3", destination="8f268cdac70e2d3")
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = ()  # vehicle is at the request
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_request = sim_updated.requests.get(request.id)
        boarded_request = updated_vehicle.vehicle_state.boarded_requests.get(request.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ServicingPoolingTrip,
            "vehicle should be in ServicingPoolingTrip state",
        )
        self.assertIsNone(
            updated_request,
            "request should no longer exist as it has been picked up",
        )
        self.assertIsNotNone(
            boarded_request,
            f"request {request.id} should have boarded the vehicle",
        )
        self.assertEqual(
            boarded_request.id,
            request.id,
            f"request {request.id} should have boarded the vehicle, "
            f"found {boarded_request.id} instead",
        )

    def test_dispatch_pooling_trip_enter_no_request(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim(vehicles=(vehicle,))  # request not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(
            updated_sim,
            "no request at location should result in no update to sim",
        )

    def test_dispatch_pooling_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_dispatch_pooling_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.geoid)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_dispatch_pooling_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchTrip.build(vehicle.id, request.id, route)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_servicing_pooling_trip_enter(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        prev_state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        error, disp_sim = prev_state.enter(sim, env)
        self.assertIsNone(error, "test invariant failed")

        # things constructed when transitioning from DispatchPoolingTrip to ServicingPoolingTrip
        boarded_trip_plan = ((request.id, TripPhase.DROPOFF),)
        boarded_reqs = immutables.Map({request.id: request})
        departure_times = immutables.Map({request.id: SimTime(0)})
        route = mock_route_from_geoids(request.origin, request.destination)
        routes = (route,)

        next_state = ServicingPoolingTrip.build(
            vehicle.id,
            boarded_trip_plan,
            boarded_reqs,
            departure_times,
            routes,
            1,
        )
        error, updated_sim = next_state.enter(disp_sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            ServicingPoolingTrip,
            "should be in a ServicingPoolingTrip state",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.routes), 1, "should have a route")

    def test_servicing_pooling_trip_update_terminal(self):
        # 3 adjacent h3 cells, total trip distance is ~ 2 meters
        vehicle = mock_vehicle_from_geoid(geoid="8f268cd9601daa1")
        request = mock_request_from_geoids(origin="8f268cd9601daac", destination="8f268cd9601da10")
        sim0 = mock_sim(vehicles=(vehicle,), sim_timestep_duration_seconds=60)

        # place request and vehicle in a mock simulation
        sim1 = simulation_state_ops.add_request_safe(sim0, request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        # set vehicle to dispatch state
        prev_state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        err2, sim2 = prev_state.enter(sim1, env)
        self.assertIsNone(err2, "test invariant failed")

        # dispatch to request (move)
        err3, sim3 = prev_state.update(sim2, env)
        self.assertIsNone(err3, "test invariant failed")
        state3 = sim3.vehicles.get(vehicle.id).vehicle_state

        # service the trip (move)
        err4, sim4 = state3.update(sim3, env)
        self.assertIsNone(err4, "test invariant failed")
        state4 = sim4.vehicles.get(vehicle.id).vehicle_state

        # drop off the trip
        err5, sim5 = state4.update(sim4, env)
        self.assertIsNone(err5, "test invariant failed")

        # test final state
        updated_vehicle = sim5.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "should be in an Idle state")
        self.assertEqual(
            len(sim5.requests),
            0,
            "request should have been picked up and dropped off fully",
        )

    def test_servicing_pooling_trip_update_picks_up_second_request(self):
        v0_src, r0_src, r1_src, r0_dst, r1_dst = (
            "8f268cd9601daa1",
            "8f268cd9601daac",
            "8f268cd9601da10",
            "8f268cd9601da1a",
            "8f268cd9601da88",
        )

        # 3 adjacent h3 cells, total trip distance is ~ 2 meters
        v0 = mock_vehicle_from_geoid(geoid=v0_src)
        r0 = mock_request_from_geoids(request_id="r0", origin=r0_src, destination=r0_dst)
        r1 = mock_request_from_geoids(request_id="r1", origin=r1_src, destination=r1_dst)
        sim0 = mock_sim(vehicles=(v0,), sim_timestep_duration_seconds=60)

        # place request and vehicle in a mock simulation
        sim1 = simulation_state_ops.add_request_safe(sim0, r0).unwrap()
        sim2 = simulation_state_ops.add_request_safe(sim1, r1).unwrap()

        env = mock_env()
        route = mock_route_from_geoids(v0.geoid, r0.geoid)
        trip_plan = (
            (r0.id, TripPhase.PICKUP),
            (r1.id, TripPhase.PICKUP),
            (r0.id, TripPhase.DROPOFF),
            (r1.id, TripPhase.DROPOFF),
        )

        # set vehicle to dispatch state
        prev_state = DispatchPoolingTrip.build(v0.id, trip_plan, route)
        err3, sim3 = prev_state.enter(sim2, env)
        self.assertIsNone(err3, "test invariant failed")

        # dispatch vehicle to first request (move)
        err4, sim4 = prev_state.update(sim3, env)
        self.assertIsNone(err4, "test invariant failed")
        state_at_req_1 = sim4.vehicles.get(v0.id).vehicle_state

        # service the trip (move), should end up picking up second request
        err5, sim5 = state_at_req_1.update(sim4, env)
        self.assertIsNone(err5, "failed to move from r0 to r1")

        veh_pooling = sim5.vehicles.get(v0.id)
        state_pooling = veh_pooling.vehicle_state
        self.assertEqual(
            veh_pooling.geoid,
            r1_src,
            "should be at the pickup location for r1",
        )
        self.assertEqual(
            len(state_pooling.boarded_requests),
            2,
            "should have 2 requests boarded",
        )
        self.assertEqual(
            state_pooling.trip_plan,
            trip_plan[2:4],
            "should have the correct remaining plan",
        )
        # todo: check state of remaining route, should be r1_src -> r0_dst, r0_dst -> r1_dst

    def test_servicing_pooling_trip_update_drops_off_first_request(self):
        v0_src, r0_src, r1_src, r0_dst, r1_dst = (
            "8f268cd9601daa1",
            "8f268cd9601daac",
            "8f268cd9601da10",
            "8f268cd9601da1a",
            "8f268cd9601da88",
        )

        # 3 adjacent h3 cells, total trip distance is ~ 2 meters
        v0 = mock_vehicle_from_geoid(geoid=v0_src)
        r0 = mock_request_from_geoids(request_id="r0", origin=r0_src, destination=r0_dst)
        r1 = mock_request_from_geoids(request_id="r1", origin=r1_src, destination=r1_dst)
        sim0 = mock_sim(vehicles=(v0,), sim_timestep_duration_seconds=60)

        # place request and vehicle in a mock simulation
        sim1 = simulation_state_ops.add_request_safe(sim0, r0).unwrap()
        sim2 = simulation_state_ops.add_request_safe(sim1, r1).unwrap()

        env = mock_env()
        route = mock_route_from_geoids(v0.geoid, r0.geoid)
        trip_plan = (
            (r0.id, TripPhase.PICKUP),
            (r1.id, TripPhase.PICKUP),
            (r0.id, TripPhase.DROPOFF),
            (r1.id, TripPhase.DROPOFF),
        )

        # set vehicle to dispatch state
        prev_state = DispatchPoolingTrip.build(v0.id, trip_plan, route)
        err3, sim3 = prev_state.enter(sim2, env)
        self.assertIsNone(err3, "test invariant failed")

        # dispatch vehicle to first request (move)
        err4, sim4 = prev_state.update(sim3, env)
        self.assertIsNone(err4, "test invariant failed")
        state_at_req_0 = sim4.vehicles.get(v0.id).vehicle_state

        # service the trip (move), should end up picking up second request
        err5, sim5 = state_at_req_0.update(sim4, env)
        self.assertIsNone(err5, "failed to move from r0 to r1")
        state_at_req_1 = sim5.vehicles.get(v0.id).vehicle_state

        # service the trip (move), should end up picking up second request
        err6, sim6 = state_at_req_1.update(sim5, env)
        self.assertIsNone(err6, "failed to move to r0 destination")

        veh_pooling = sim6.vehicles.get(v0.id)
        state_pooling = veh_pooling.vehicle_state
        self.assertEqual(
            veh_pooling.geoid,
            r0_dst,
            "should be at the dropoff location for r0",
        )
        self.assertEqual(
            len(state_pooling.boarded_requests),
            1,
            "should have 1 requests still boarded",
        )
        self.assertIsNone(
            sim6.requests.get("r0"),
            "request 0 should have been dropped off and no longer be in the simulation",
        )
        self.assertEqual(
            state_pooling.trip_plan,
            trip_plan[3:4],
            "should have the correct remaining plan",
        )
        # todo: check state of remaining route, should be r0_dst -> r1_dst

    def test_servicing_single_pooling_trip_reaches_destination(self):
        vehicle = mock_vehicle()
        request = mock_request()
        sim = simulation_state_ops.add_request_safe(mock_sim(vehicles=(vehicle,)), request).unwrap()
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.geoid)
        trip_plan = (
            (request.id, TripPhase.PICKUP),
            (request.id, TripPhase.DROPOFF),
        )

        state = DispatchPoolingTrip.build(vehicle.id, trip_plan, route)
        error, updated_sim = state.enter(sim, env)
        entered_state = updated_sim.vehicles.get(vehicle.id).vehicle_state

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        updated_request = updated_sim.requests.get(request.id)
        self.assertIsInstance(
            updated_vehicle.vehicle_state,
            DispatchPoolingTrip,
            "should be in a dispatch to request state",
        )
        self.assertEqual(
            updated_request.dispatched_vehicle,
            vehicle.id,
            "request should be assigned this vehicle",
        )
        self.assertEqual(len(updated_vehicle.vehicle_state.route), 1, "should have a route")
        self.assertEqual(
            entered_state.instance_id,
            updated_vehicle.vehicle_state.instance_id,
            "should be the same instance",
        )

    def test_servicing_pooling_trip_exit(self):
        """
        cannot run until exit is supported, should only be supported under the condition of going to
        an updated ServicingPoolingTrip (see https://github.com/NREL/hive/issues/27)
        """
        pass

    def test_servicing_pooling_trip_exit_when_still_has_passengers(self):
        """
        see above
        """
        pass

    def test_servicing_pooling_trip_exit_when_still_has_passengers_but_out_of_fuel(
        self,
    ):
        """
        see above
        """
        pass

    def test_servicing_pooling_trip_update(self):
        """
        see above
        """
        pass
