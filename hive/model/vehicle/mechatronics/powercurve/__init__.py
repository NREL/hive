from hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve
from hive.model.vehicle.mechatronics.powercurve.tabular_powercurve import TabularPowercurve

powercurve_models = {
    'tabular': TabularPowercurve
}


def build_powercurve(config: dict) -> Powercurve:
    try:
        name = config['powercurve_type']
    except KeyError:
        raise AttributeError("Can't build powercurve without powercurve type")

    if name not in powercurve_models:
        raise IOError(f"PowerCurve with name {name} is not recognized, must be one of {powercurve_models.keys()}")
    else:
        return powercurve_models[name](config=config)
