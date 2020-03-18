from typing import Tuple, Optional, NamedTuple

from hive.util.exception import SimulationStateError

from hive.util.typealiases import StationId

from hive.model.energy.charger import Charger

from hive import SimulationState, Environment, VehicleId
from hive.model.vehicle.vehicle_state.vehicle_state import VehicleState


class Charging(NamedTuple, VehicleState):
    """
    a vehicle is charging at a station with a specific charger type
    """
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def enter(self,
              sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        entering a charge event requires attaining a charger from the station
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        # ok, we want to enter a charging state.
        # we attempt to claim a charger from the station of this self.charger type
        # what if we can't? is that an Exception, or, is that simply rejected?
        station = sim.stations.get(self.station_id)

        if not station:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            updated_station = station.checkout_charger(self.charger)
            if not updated_station:
                return None, None
            else:
                updated_sim = sim.modify_station(updated_station)
                return VehicleState.default_enter(updated_sim, self.vehicle_id, self)

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def exit(self,
             sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        exiting a charge event requires returning the charger to the station
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        station = sim.stations.get(self.station_id)

        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not station:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            updated_station = station.return_charger(self.charger)
            updated_sim = sim.modify_station(updated_station)
            return None, updated_sim

    def _has_reached_terminal_state_condition(self,
                                              sim: SimulationState,
                                              env: Environment) -> bool:
        """
        test if charging is finished
        :param sim: the simulation state
        :param env: the simulation environment
        :return: True if the vehicle is fully charged
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not vehicle:
            return False
        else:
            return vehicle.energy_source.is_at_ideal_energy_limit()

    def _default_transition(self,
                            sim: SimulationState,
                            env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply a transition to a default state after having met a terminal condition
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            # are we at a base?
            bases = sim.at_geoid(vehicle.geoid).get("bases")
            base_id = bases[0] if bases else None

            if base_id:
                next_state = ReserveBase(self.vehicle_id)
                return next_state.enter(sim, env)
            else:
                next_state = Idle(self.vehicle_id)
                return next_state.enter(sim, env)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState
        :param sim: the simulation state
        :param env: the simulation environment
        :param self.vehicle_id: the vehicle transitioning
        :return: an exception due to failure or an optional updated simulation
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        powercurve = env.powercurves.get(vehicle.powercurve_id) if vehicle else None
        station = sim.stations.get(self.station_id)

        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not powercurve:
            return SimulationStateError(f"invalid powercurve_id {vehicle.powercurve_id}"), None
        elif not station:
            return SimulationStateError(f"station {self.station_id} not found"), None
        elif vehicle.energy_source.is_at_ideal_energy_limit():
            return SimulationStateError(f"vehicle {self.vehicle_id} is full but still attempting to charge"), None
        else:
            # charge energy source
            updated_energy_source = powercurve.refuel(
                vehicle.energy_source,
                self.charger,
                sim.sim_timestep_duration_seconds
            )

            # determine price of charge event
            kwh_transacted = updated_energy_source.energy_kwh - vehicle.energy_source.energy_kwh  # kwh
            charger_price = station.charger_prices.get(self.charger)  # Currency
            charging_price = kwh_transacted * charger_price if charger_price else 0.0

            # perform updates
            updated_vehicle = vehicle.modify_energy_source(updated_energy_source).send_payment(charging_price)
            updated_station = station.receive_payment(charging_price)
            updated_sim = sim.modify_vehicle(updated_vehicle).modify_station(updated_station)

            return None, updated_sim
