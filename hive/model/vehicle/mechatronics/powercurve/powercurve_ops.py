from hive.model.energy.charger import Charger
from hive.model.vehicle.vehicle import Vehicle
from hive.model.vehicle.mechatronics import MechatronicsInterface
from hive.util import Seconds, Ratio


def time_to_full(
        vehicle: Vehicle,
        mechatronics: MechatronicsInterface,
        charger: Charger,
        target_soc: Ratio,
        sim_timestep_duration_seconds: Seconds,
) -> Seconds:
    """
    fills an imaginary vehicle in order to determine the estimated time to charge

    :param vehicle: a vehicle to estimate
    :param mechatronics: the physics of this vehicle
    :param charger: the charger used
    :param target_soc: the stopping condition, a target vehicle SoC percentage
    :param sim_timestep_duration_seconds: the stride, in seconds, of the simulation
    :return: the time to charge
    """
    def _fill(charging_vehicle: Vehicle, time_charged_accumulator: Seconds = 0) -> Seconds:
        if mechatronics.fuel_source_soc(charging_vehicle) >= target_soc:
            return time_charged_accumulator
        else:
            updated_veh, time_delta = mechatronics.add_energy(charging_vehicle,
                                                              charger,
                                                              sim_timestep_duration_seconds)
            updated_time_charged_acc = time_charged_accumulator + time_delta
            return _fill(updated_veh, updated_time_charged_acc)

    time_charged = _fill(vehicle)

    return time_charged

