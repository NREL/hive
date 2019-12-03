from typing import Union

import yaml
from pkg_resources import resource_string

from hive.model.energy.powercurve.powercurve import PowerCurve
from hive.model.energy.powercurve.tabular_powercurve import TabularPowerCurve

__doc__ = """

"""

powercurve_models = {
    'leaf': resource_string('hive.resources.powercurve', 'leaf.yaml')
}

powercurve_constructors = {
    'tabular': TabularPowerCurve
}


def build_powercurve(name: str) -> Union[IOError, PowerCurve]:
    """
    constructs EnergyCurve objects from file descriptions
    :param name: name of a valid energy curve type
    :return: an EnergyCurve, or, an error
    :raise IOError: if model file is invalid
    """
    if name not in powercurve_models:
        return IOError(f"EnergyCurve with name {name} is not recognized, must be one of {powercurve_models.keys()}")
    else:
        file_path = powercurve_models[name]
        energycurve_config = yaml.safe_load(file_path)
        model_type = energycurve_config["type"]
        return powercurve_constructors[model_type](energycurve_config)
