from unittest import TestCase

from hive.state.vehicle_state import *
from tests.mock_lobster import *
from hive.model.passenger import board_vehicle


class TestVehicleState(TestCase):

    ####################################################################################################################
    # ChargingStation ##################################################################################################
    ####################################################################################################################

    def test_charging_station_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
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
        self.assertEquals(available_chargers, 0, "should have claimed the only DCFC charger")

    def test_charging_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
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
        self.assertEquals(available_chargers, 1, "should have returned the only DCFC charger")

    def test_charging_station_update(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
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
            first=updated_vehicle.energy_source.energy_kwh,
            second=vehicle.energy_source.energy_kwh + 0.83,
            places=2,
            msg="should have charged for 60 seconds")

    def test_charging_station_update_terminal(self):
        vehicle = mock_vehicle(soc=0.99)
        station = mock_station()
        charger = Charger.DCFC
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
        self.assertEquals(updated_station.available_chargers.get(charger), 1, "should have returned the charger")

    def test_charging_station_enter_with_no_station(self):
        vehicle = mock_vehicle(soc=0.99)
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle,),
        )
        env = mock_env()

        state = ChargingStation(vehicle.id, DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_charging_station_enter_with_no_vehicle(self):
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            stations=(station,),
        )
        env = mock_env()

        state = ChargingStation(DefaultIds.mock_vehicle_id(), DefaultIds.mock_station_id(), charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    ####################################################################################################################
    # ChargingBase #####################################################################################################
    ####################################################################################################################

    def test_charging_base_enter(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = Charger.DCFC
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
        self.assertEquals(available_chargers, 0, "should have claimed the only DCFC charger")

    def test_charging_base_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = Charger.DCFC
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
        self.assertEquals(available_chargers, 1, "should have returned the only DCFC charger")

    def test_charging_base_update(self):
        vehicle = mock_vehicle()
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = Charger.DCFC
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
            first=updated_vehicle.energy_source.energy_kwh,
            second=vehicle.energy_source.energy_kwh + 0.83,
            places=2,
            msg="should have charged for 60 seconds")

    def test_charging_base_update_terminal(self):
        vehicle = mock_vehicle(soc=1.0)
        station = mock_station()
        base = mock_base(station_id=DefaultIds.mock_station_id())
        charger = Charger.DCFC
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
        charger = Charger.DCFC
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
        charger = Charger.DCFC
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
        charger = Charger.DCFC
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
        charger = Charger.DCFC
        sim = mock_sim(
            stations=(station,),
            bases=(base,)
        )
        env = mock_env()

        state = ChargingBase(DefaultIds.mock_vehicle_id(), base.id, charger)
        enter_error, sim_with_charging_vehicle = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

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
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchBase,
                              "should still be in a dispatch to base state")
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")

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
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
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

    def test_dispatch_station_exit(self):
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
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
        charger = Charger.DCFC
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
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, DispatchStation,
                              "should still be in a dispatch to station state")
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")

    def test_dispatch_station_update_terminal(self):
        initial_soc = 0.1
        vehicle = mock_vehicle(soc=initial_soc)
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,)
        )
        env = mock_env()
        route = ()  # empty route should trigger a default transition

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, sim_with_dispatch_vehicle = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_with_dispatch_vehicle, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        updated_station = sim_updated.stations.get(station.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ChargingStation,
                              "vehicle should be in ChargingStation state")
        self.assertEquals(updated_station.available_chargers.get(charger), 0,
                          "should have taken the only available charger")
        self.assertGreater(updated_vehicle.energy_source.soc, initial_soc, "should have charged for one time step")

    def test_dispatch_station_enter_no_station(self):
        vehicle = mock_vehicle()
        charger = Charger.DCFC
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
        charger = Charger.DCFC
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
        station = mock_station()
        charger = Charger.DCFC
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
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        station = mock_station()
        charger = Charger.DCFC
        sim = mock_sim(
            vehicles=(vehicle,),
            stations=(station,),
        )
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)

        state = DispatchStation(vehicle.id, station.id, route, charger)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

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
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")

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
        vehicle = mock_vehicle().modify_state(DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, Idle, "should be in an idle to request state")

    def test_idle_exit(self):
        # should intially not be in an Idle state
        vehicle = mock_vehicle().modify_state(DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
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
        vehicle = mock_vehicle().modify_state(DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ()))
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
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")
        self.assertEqual(updated_vehicle.vehicle_state.idle_duration,
                         sim.sim_timestep_duration_seconds,
                         "should have recorded the idle time")

    def test_idle_update_terminal(self):
        initial_soc = 0.0
        ititial_state = DispatchBase(DefaultIds.mock_vehicle_id(), DefaultIds.mock_base_id(), ())
        vehicle = mock_vehicle(soc=initial_soc).modify_state(ititial_state)
        sim = mock_sim(vehicles=(vehicle,))
        env = mock_env()

        state = Idle(vehicle.id)
        enter_error, updated_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(updated_sim, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, OutOfService, "vehicle should be OutOfService")
        self.assertTrue(updated_vehicle.energy_source.is_empty, "vehicle should have no energy")

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
        self.assertEqual(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have the same energy")

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
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")

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
        self.assertEqual(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have the same energy")

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
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, request.destination)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")

        updated_vehicle = updated_sim.vehicles.get(vehicle.id)
        self.assertIsInstance(updated_vehicle.vehicle_state, ServicingTrip, "should be in a ServicingTrip state")
        self.assertEquals(len(updated_vehicle.vehicle_state.route), 1, "should have a route")

    def test_servicing_trip_exit(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(destination=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")  # errors due to passengers not being at destination

    def test_servicing_trip_exit_when_still_has_passengers(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids()
        self.assertNotEqual(request.origin, request.destination, "test invariant failed")
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)

        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(request.origin, request.destination)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, entered_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        # begin test
        error, exited_sim = state.exit(entered_sim, env)

        self.assertIsNone(error, "should have no errors")  # errors due to passengers not being at destination
        self.assertIsNone(exited_sim, "should not have allowed exit of ServicingTrip")

    def test_servicing_trip_update(self):
        near = h3.geo_to_h3(39.7539, -104.974, 15)
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid(geoid=near)
        request = mock_request_from_geoids(origin=near, destination=omf_brewing)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(near, omf_brewing)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, sim_servicing = state.enter(sim, env)
        self.assertIsNone(enter_error, "test precondition (enter works correctly) not met")

        update_error, sim_updated = state.update(sim_servicing, env)
        self.assertIsNone(update_error, "should have no error from update call")

        updated_vehicle = sim_updated.vehicles.get(vehicle.id)
        self.assertNotEqual(vehicle.geoid, updated_vehicle.geoid, "should have moved")
        self.assertIsInstance(updated_vehicle.vehicle_state, ServicingTrip, "should still be in a servicing state")
        self.assertLess(updated_vehicle.energy_source.soc, vehicle.energy_source.soc, "should have less energy")
        self.assertEqual(updated_vehicle.vehicle_state.passengers, request.passengers, "should have passengers")

    def test_servicing_trip_update_terminal(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=vehicle.geoid, destination=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = ()  # end of route

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
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

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        error, updated_sim = state.enter(sim, env)

        self.assertIsNone(error, "should have no errors")
        self.assertIsNone(updated_sim, "no request at location should result in no update to sim")

    def test_servicing_trip_enter_no_vehicle(self):
        vehicle = mock_vehicle()
        request = mock_request_from_geoids(origin=vehicle.geoid)
        sim = mock_sim()  # vehicle not added to sim
        env = mock_env()
        route = mock_route_from_geoids(request.geoid, request.destination)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, updated_sim = state.enter(sim, env)

        self.assertIsInstance(enter_error, Exception, "should have exception")

    def test_servicing_trip_enter_route_with_bad_source(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle()
        request = mock_request()
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(omf_brewing, request.destination)

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, enter_sim = state.enter(sim, env)

        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    def test_servicing_trip_enter_route_with_bad_destination(self):
        omf_brewing = h3.geo_to_h3(39.7608873, -104.9845391, 15)
        vehicle = mock_vehicle_from_geoid()
        request = mock_request_from_geoids(origin=vehicle.geoid)
        e1, sim = simulation_state_ops.add_request(mock_sim(vehicles=(vehicle,)), request)
        self.assertIsNone(e1, "test invariant failed")
        env = mock_env()
        route = mock_route_from_geoids(vehicle.geoid, omf_brewing)  # request.destination should not be omf brewing co

        state = ServicingTrip(vehicle.id, request.id, route, request.passengers)
        enter_error, enter_sim = state.enter(sim, env)
        self.assertIsNone(enter_error, "should be no error")
        self.assertIsNone(enter_sim, "invalid route should have not changed sim state")

    ####################################################################################################################
    # ChargeQueueing ###################################################################################################
    ####################################################################################################################

    def test_charge_queueing_enter(self):
        vehicle_charging = mock_vehicle_from_geoid()
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, Charger.DCFC)
        e1, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, Charger.DCFC)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")

        # should have inserted self into queue

    def test_charge_queueing_exit(self):
        vehicle_charging = mock_vehicle_from_geoid()
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, Charger.DCFC)
        e1, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, Charger.DCFC)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "test invariant failed")

        # should remove self from queue

    def test_charge_queueing_update(self):
        vehicle_charging = mock_vehicle_from_geoid()
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, Charger.DCFC)
        e1, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, Charger.DCFC)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")

        # update should apply idle cost if stall is still not available

    def test_charge_queueing_update_terminal(self):
        vehicle_charging = mock_vehicle_from_geoid()
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_charging, vehicle_queueing,))
        env = mock_env()

        charging_state = ChargingStation(vehicle_charging.id, station.id, Charger.DCFC)
        e1, sim2 = charging_state.update(sim1, env)
        self.assertIsNone(e1, "test invariant failed")

        state = ChargeQueueing(vehicle_queueing.id, station.id, Charger.DCFC)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")

        # should have removed self from queue and moved to ChargingStation if available
        #  otherwise, never ends

    def test_charge_queueing_enter_no_vehicle(self):
        station = mock_station_from_geoid()
        sim0 = mock_sim()
        env = mock_env()

        charging_state = ChargingStation(DefaultIds.mock_vehicle_id(), station.id, Charger.DCFC)
        err1, sim1 = charging_state.update(sim0, env)
        self.assertIsNone(err1, "test invariant failed")

        state = ChargeQueueing(DefaultIds.mock_vehicle_id(), station.id, Charger.DCFC)
        err2, sim2 = state.enter(sim1, env)

        self.assertIsInstance(err2, Exception, "should have exception")

    def test_charge_queueing_enter_when_station_has_charger_available(self):
        vehicle_queueing = mock_vehicle_from_geoid()
        station = mock_station_from_geoid()
        sim1 = mock_sim(vehicles=(vehicle_queueing,))
        env = mock_env()

        state = ChargeQueueing(vehicle_queueing.id, station.id, Charger.DCFC)
        error, updated_sim = state.enter(sim1, env)

        self.assertIsNone(error, "should have no errors")

        # should fail as a bunk instruction but not be an error