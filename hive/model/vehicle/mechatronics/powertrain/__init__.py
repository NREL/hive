from hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from hive.model.vehicle.mechatronics.powertrain.tabular_powertrain import TabularPowertrain

powertrain_models = {
    'tabular': TabularPowertrain
}


def build_powertrain(config: dict) -> Powertrain:
    try:
        name = config['powertrain_type']
    except KeyError:
        raise AttributeError("Can't build powertrain without powertrain type")

    if name not in powertrain_models:
        raise IOError(f"PowerCurve with name {name} is not recognized, must be one of {powertrain_models.keys()}")
    else:
        return powertrain_models[name](config=config)
