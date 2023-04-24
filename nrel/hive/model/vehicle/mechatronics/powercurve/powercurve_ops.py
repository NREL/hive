import logging

from nrel.hive.model.energy.charger import Charger
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.model.vehicle.mechatronics import MechatronicsInterface
from nrel.hive.util import Seconds, Ratio

log = logging.getLogger(__file__)


def time_to_full(
    vehicle: Vehicle,
    mechatronics: MechatronicsInterface,
    charger: Charger,
    target_soc: Ratio,
    sim_timestep_duration_seconds: Seconds,
    min_delta_energy_change: Ratio,
) -> Seconds:
    """
    fills an imaginary vehicle in order to determine the estimated time to charge
    Calculating a delta because vehicles take a long time to reach a value of 100%

    :param vehicle: a vehicle to estimate
    :param mechatronics: the physics of this vehicle
    :param charger: the charger used
    :param target_soc: the stopping condition, a target vehicle State of Charge percentage
    :param sim_timestep_duration_seconds: the stride, in seconds, of the simulation
    :param min_delta_energy_change: minimum change in vehicle energy before breaking loop and charging stopped
    :return: the time to charge

    #TODO: to deal with the grid throttle scenario, what might be a good thing in the future would be to pass
    #some max charge time argument. that at least can be set to
    #int((sim.end_time - sim.sim_time) / sim.timestep_duration_seconds) .
    """
    if charger.energy_type not in vehicle.energy:
        raise Exception(
            f"Charger energy type is not in vehicle.energy,\n"
            "needed for is_full calculation {charger.energy_type} {vehicle.energy}"
        )
    time_charged = 0
    delta = 1.0  # setting default to pass the first time
    while (
        not mechatronics.fuel_source_soc(vehicle) >= target_soc and delta > min_delta_energy_change
    ):
        prev_energy = vehicle.energy.get(charger.energy_type)

        vehicle, time_delta = mechatronics.add_energy(
            vehicle, charger, sim_timestep_duration_seconds
        )
        if prev_energy != 0:
            cur_energy = vehicle.energy.get(charger.energy_type)
            if prev_energy is not None and cur_energy is not None:
                delta = abs(prev_energy - cur_energy) / prev_energy
        time_charged += time_delta
    return time_charged
