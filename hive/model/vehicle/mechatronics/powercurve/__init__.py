from pathlib import Path

import yaml

from hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve
from hive.model.vehicle.mechatronics.powercurve.tabular_powercurve import TabularPowercurve

powercurve_models = {
    'tabular': TabularPowercurve
}


def build_powercurve(config: dict) -> Powercurve:
    try:
        file = config['powercurve_file']
    except KeyError:
        raise AttributeError("Can't build powercurve without powercurve file")

    with Path(config['powercurve_file']).open() as f:
        powertrain_file_contents = yaml.safe_load(f)
        powercurve_type = powertrain_file_contents.get('type')
        if not powercurve_type:
            raise KeyError(f"powertrain file {file} missing required 'type' field")
        if powercurve_type not in powercurve_models:
            raise IOError(f"PowerCurve with type {powercurve_type} is not recognized, must be one of {powercurve_models.keys()}")
        else:
            return powercurve_models[powercurve_type](config=config)
