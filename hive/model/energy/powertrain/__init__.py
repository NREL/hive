from typing import Union

import yaml
from pkg_resources import resource_string

from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.energy.powertrain.bev_tabular_powertrain import BEVTabularPowertrain

__doc__ = """

"""

powertrain_models = {
    'leaf': resource_string('hive.resources.powertrain', 'leaf.yaml')
}

powertrain_constructors = {
    'bev_tabular': BEVTabularPowertrain
}


def build_powertrain(name: str) -> Union[IOError, Powertrain]:
    """
    constructs powertrain objects from file descriptions
    :param name: name of a valid powertrain type
    :return: a Powertrain, or, an error
    """
    if name not in powertrain_models:
        return IOError(
            f"Powertrain with name {name} is not recognized; must be one of {list(powertrain_models)}")
    else:
        file_path = powertrain_models[name]
        powertrain_config = yaml.safe_load(file_path)
        model_type = powertrain_config["type"]
        return powertrain_constructors[model_type](powertrain_config)
