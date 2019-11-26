from typing import Union

import yaml
from pkg_resources import resource_string

from hive.model.energy.energycurve.energycurve import EnergyCurve
from hive.model.energy.energycurve.tabular_energycurve import TabularEnergyCurve

__doc__ = """

"""

energycurve_models = {
    'leaf': resource_string('hive.resources.energycurve', 'leaf.yaml')
}

energycurve_constructors = {
    'tabular': TabularEnergyCurve
}


def build_energycurve(name: str) -> Union[IOError, EnergyCurve]:
    """
    constructs EnergyCurve objects from file descriptions
    :param name: name of a valid energy curve type
    :return: an EnergyCurve, or, an error
    :raise IOError: if model file is invalid
    """
    if name not in energycurve_models:
        return IOError(f"EnergyCurve with name {name} is not recognized, must be one of {energycurve_models.keys()}")
    else:
        file_path = energycurve_models[name]
        energycurve_config = yaml.safe_load(file_path)
        model_type = energycurve_config["type"]
        return energycurve_constructors[model_type](energycurve_config)
