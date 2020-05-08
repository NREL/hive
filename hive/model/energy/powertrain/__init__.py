import yaml
from pkg_resources import resource_string

from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.energy.powertrain.tabular_powertrain import TabularPowertrain

__doc__ = """

"""

powertrain_models = {
    'normalized': resource_string('hive.resources.powertrain', 'normalized.yaml')
}

powertrain_constructors = {
    'tabular': TabularPowertrain
}


def build_powertrain(name: str,) -> Powertrain:
    """
    constructs powertrain objects from file descriptions

    :param name: name of a valid powertrain type
    :return: a Powertrain, or, an error
    :raise IOError: if model file is invalid
    """
    if name not in powertrain_models:
        raise IOError(
            f"Powertrain with name {name} is not recognized; must be one of {powertrain_models.keys()}")
    else:
        file_path = powertrain_models[name]
        powertrain_config = yaml.safe_load(file_path)
        model_type = powertrain_config["type"]
        return powertrain_constructors[model_type](powertrain_config)
