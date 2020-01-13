from csv import DictReader
from unittest import TestCase

from hive.model.vehiclestate import VehicleState
from tests.mock_lobster import *


class TestVehicle(TestCase):
    def test_has_passengers(self):
        updated_vehicle = mock_vehicle().add_passengers(mock_request().passengers)
        self.assertEqual(updated_vehicle.has_passengers(), True, "should have passengers")

    def test_has_route(self):
        updated_vehicle = mock_vehicle()._replace(route=mock_route())
        self.assertEqual(updated_vehicle.has_route(), True, "should have a route")

    def test_add_passengers(self):
        no_pass_veh = mock_vehicle()
        mock_req = mock_request()

        with_pass_veh = no_pass_veh.add_passengers(mock_req.passengers)
        self.assertEqual(len(with_pass_veh.passengers), len(mock_req.passengers))

    def test_battery_swap(self):
        veh = mock_vehicle()
        new_soc = 0.99
        batt = mock_energy_source(soc=new_soc)
        updated_vehicle = veh.battery_swap(batt)

        self.assertEqual(updated_vehicle.energy_source.soc, new_soc, "should have the new battery's soc")

    def test_transition_idle(self):
        non_idling_vehicle = mock_vehicle()._replace(route=mock_route(),
                                                     vehicle_state=VehicleState.REPOSITIONING)
        transitioned = non_idling_vehicle.transition(VehicleState.IDLE)
        self.assertEqual(transitioned.vehicle_state, VehicleState.IDLE, "should have transitioned into an idle state")

    def test_transition_repositioning(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.REPOSITIONING)
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_trip(self):
        """
        given a Vehicle in an IDLE state,
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the vehicle state is correctly updated
        """
        idle_vehicle = mock_vehicle()

        # check on transition function result
        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_servicing_trip(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.SERVICING_TRIP)

        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_station(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_charging_station(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_STATION)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_base(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_charging_base(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_reserve_base(self):
        idle_vehicle = mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.RESERVE_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_can_transition_good(self):
        idle_veh = mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.IDLE)

        veh_can_trans = veh_serving_trip.can_transition(VehicleState.DISPATCH_TRIP)

        self.assertEqual(veh_can_trans, True)

    def test_can_transition_bad(self):
        mock_req = mock_request()
        idle_veh = mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.SERVICING_TRIP)
        veh_w_pass = veh_serving_trip.add_passengers(mock_req.passengers)

        veh_can_trans = veh_w_pass.can_transition(VehicleState.IDLE)

        self.assertEqual(veh_can_trans, False, "shouldn't be able to go IDLE with passengers aboard")

    def test_move(self):
        # approx 8.5 km distance.
        somewhere = h3.geo_to_h3(39.75, -105.1, 15)
        somewhere_else = h3.geo_to_h3(39.75, -105, 15)

        vehicle = mock_vehicle_from_geoid(geoid=somewhere).transition(VehicleState.REPOSITIONING)
        power_train = mock_powertrain()
        road_network = mock_network()

        start = road_network.property_link_from_geoid(somewhere)
        end = road_network.property_link_from_geoid(somewhere_else)

        route = road_network.route(start, end)

        vehicle_w_route = vehicle.assign_route(route)

        moved_vehicle = vehicle_w_route.move(road_network=road_network,
                                             power_train=power_train,
                                             time_step=400 * unit.seconds)
        m2 = moved_vehicle.move(road_network=road_network,
                                power_train=power_train,
                                time_step=400 * unit.seconds)
        # vehicle should have arrived after second move.
        m3 = m2.move(road_network=road_network,
                     power_train=power_train,
                     time_step=10 * unit.seconds)

        self.assertLess(moved_vehicle.energy_source.soc, 1)
        self.assertNotEqual(somewhere, moved_vehicle.geoid)
        self.assertNotEqual(somewhere, moved_vehicle.property_link.link.start)

        self.assertNotEqual(moved_vehicle.geoid, m2.geoid)
        self.assertNotEqual(moved_vehicle.property_link.link.start, m2.property_link.link.start)

        self.assertEqual(m3.vehicle_state, VehicleState.IDLE, 'Vehicle should have finished route')
        self.assertGreater(m3.distance_traveled, 8.5 * unit.kilometer, 'Vehicle should have traveled around 8km')

    def test_charge(self):
        vehicle = mock_vehicle().transition(VehicleState.CHARGING_STATION).plug_in_to('s1', Charger.DCFC)
        power_curve = mock_powercurve()
        time_step_size_secs = 1.0 * unit.seconds

        result = vehicle.charge(power_curve, time_step_size_secs)
        self.assertAlmostEqual(
            first=result.energy_source.energy,
            second=vehicle.energy_source.energy + 0.01 * unit.kilowatthour,
            places=2,
            msg="should have charged")

    def test_charge_when_full(self):
        vehicle = mock_vehicle(
            capacity=100 * unit.kilowatthour,
            soc=1.0
        ).transition(VehicleState.CHARGING_STATION).plug_in_to('s1', Charger.DCFC)
        # vehicle_full = vehicle.battery_swap(TestVehicle.mock_energysource(cap=100 * unit.kilowatthour,
        #                                                                   soc=1.0))  # full
        power_curve = mock_powercurve()
        time_step_size_secs = 1.0 * unit.seconds

        result = vehicle.charge(power_curve, time_step_size_secs)
        self.assertEqual(result.energy_source.energy, vehicle.energy_source.energy, "should have not charged")

    def test_idle(self):
        idle_vehicle = mock_vehicle()
        idle_vehicle_less_energy = idle_vehicle.idle(60 * unit.seconds)  # idle for 60 seconds

        self.assertLess(idle_vehicle_less_energy.energy_source.soc, idle_vehicle.energy_source.soc,
                        "Idle vehicles should have consumed energy.")
        self.assertEqual(idle_vehicle_less_energy.idle_time_s, 60 * unit.seconds, "Should have recorded idle time.")

    def test_idle_reset(self):
        idle_vehicle = mock_vehicle().idle(60 * unit.seconds)

        dispatch_vehicle = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)

        self.assertEqual(dispatch_vehicle.idle_time_s, 0 * unit.seconds, "Should have reset idle time.")

    def test_from_row(self):
        source = """vehicle_id,lat,lon,powertrain_id,powercurve_id,capacity,ideal_energy_limit,max_charge_acceptance,initial_soc
                    v1,37,122,leaf,leaf,50.0,40,50,1.0"""

        row = next(DictReader(source.split()))
        road_network = HaversineRoadNetwork()
        expected_geoid = h3.geo_to_h3(37, 122, road_network.sim_h3_resolution)

        vehicle = Vehicle.from_row(row, road_network)

        self.assertEqual(vehicle.id, "v1")
        self.assertEqual(vehicle.geoid, expected_geoid)
        self.assertEqual(vehicle.powercurve_id, 'leaf')
        self.assertEqual(vehicle.powertrain_id, 'leaf')
        self.assertEqual(vehicle.energy_source.powercurve_id, 'leaf')
        self.assertEqual(vehicle.energy_source.ideal_energy_limit, 40.0 * unit.kilowatthours)
        self.assertEqual(vehicle.energy_source.energy, 50.0 * unit.kilowatthours)
        self.assertEqual(vehicle.energy_source.capacity, 50.0 * unit.kilowatthours)
        self.assertEqual(vehicle.energy_source.energy_type, EnergyType.ELECTRIC)
        self.assertEqual(vehicle.energy_source.max_charge_acceptance_kw, 50.0 * unit.kilowatt)
        self.assertEqual(len(vehicle.passengers), 0)
        self.assertEqual(vehicle.property_link.start, expected_geoid)
        self.assertEqual(vehicle.vehicle_state, VehicleState.IDLE)
        self.assertEqual(vehicle.distance_traveled, 0)
        self.assertEqual(vehicle.idle_time_s, 0)
        self.assertEqual(vehicle.route, ())
        self.assertEqual(vehicle.station, None)
        self.assertEqual(vehicle.station_intent, None)
        self.assertEqual(vehicle.plugged_in_charger, None)
        self.assertEqual(vehicle.charger_intent, None)

    def test_from_row_bad_powertrain_id(self):
        source = """vehicle_id,lat,lon,powertrain_id,powercurve_id,capacity,ideal_energy_limit,max_charge_acceptance,initial_soc
                    v1,37,122,beef!@#$,leaf,50.0,40,50,1.0"""

        row = next(DictReader(source.split()))
        road_network = HaversineRoadNetwork()

        with self.assertRaises(IOError):
            Vehicle.from_row(row, road_network)

    def test_from_row_bad_powercurve_id(self):
        source = """vehicle_id,lat,lon,powertrain_id,powercurve_id,capacity,ideal_energy_limit,max_charge_acceptance,initial_soc
                    v1,37,122,leaf,asdjfkl;asdfjkl;,50.0,40,50,1.0"""

        row = next(DictReader(source.split()))
        road_network = HaversineRoadNetwork()

        with self.assertRaises(IOError):
            Vehicle.from_row(row, road_network)
