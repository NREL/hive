import yaml
from pkg_resources import resource_string

from hive.model.energy.energytype import EnergyType
from hive.model.energy.powercurve.powercurve import Powercurve
from hive.model.energy.powercurve.tabular_powercurve import TabularPowercurve

__doc__ = """

"""

powercurve_models = {
    'leaf': resource_string('hive.resources.powercurve', 'leaf.yaml')
}

powercurve_constructors = {
    'tabular': TabularPowercurve
}

powercurve_energy_types = {
    'leaf': EnergyType.ELECTRIC
}


def build_powercurve(name: str) -> Powercurve:
    """
    constructs EnergyCurve objects from file descriptions

    :param name: name of a valid energy curve type
    :return: an EnergyCurve, or, an error
    :raise IOError: if model file is invalid
    """
    if name not in powercurve_models:
        raise IOError(f"EnergyCurve with name {name} is not recognized, must be one of {powercurve_models.keys()}")
    else:
        file_path = powercurve_models[name]
        energycurve_config = yaml.safe_load(file_path)
        model_type = energycurve_config["type"]
        return powercurve_constructors[model_type](energycurve_config)