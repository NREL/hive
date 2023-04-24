from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import yaml
from immutables import Map

from nrel.hive.model.vehicle.mechatronics.bev import BEV
from nrel.hive.model.vehicle.mechatronics.ice import ICE
from nrel.hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from nrel.hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve
from nrel.hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from nrel.hive.util import fs
from nrel.hive.util.typealiases import MechatronicsId


def build_mechatronics_table(
    mechatronics_file: str,
    scenario_directory: str,
    custom_powertrain_constructor: Optional[Callable[[Dict[str, Any]], Powertrain]] = None,
    custom_powercurve_constructor: Optional[Callable[[Dict[str, Any]], Powercurve]] = None,
) -> Map[MechatronicsId, MechatronicsInterface]:
    """
    constructs a dictionary containing all of the provided vehicle configurations where the key is the mechatronics ID
    and the contents are the appropriate mechatronics models with the desired attributes


    :param mechatronics_file: the mechatronics configuration yaml file

    :param scenario_directory: the directory with the required scenario files
    :return: a dictionary of the different vehicle configurations where the keys are the mechatronics IDs
    :raises Exception due to IOErrors, missing required parameters in the mechatronics yaml
    :raises Exception due to FileNotFoundErrors, missing the mechatronics, powertrain, or powercurve file(s)
    """
    mechatronics: Dict[str, MechatronicsInterface] = {}
    with open(mechatronics_file) as f:
        config_dict = yaml.safe_load(f)
        for mechatronics_id in config_dict:
            # add the mechatronics id to the nested dictionary
            config_dict[mechatronics_id]["mechatronics_id"] = mechatronics_id
            try:
                mechatronics_type = config_dict[mechatronics_id]["mechatronics_type"]
            except KeyError:
                raise IOError(f"could not find mechatronics_type in {mechatronics_id}")

            if "powertrain_file" in config_dict[mechatronics_id]:
                powertrain_file = fs.construct_asset_path(
                    config_dict[mechatronics_id]["powertrain_file"],
                    scenario_directory,
                    "powertrain",
                    "powertrain",  # resources.powertrain
                )
                config_dict[mechatronics_id]["powertrain_file"] = powertrain_file

            if "powercurve_file" in config_dict[mechatronics_id]:
                powercurve_file = fs.construct_asset_path(
                    config_dict[mechatronics_id]["powercurve_file"],
                    scenario_directory,
                    "powercurve",
                    "powercurve",  # resources.powercurve
                )
                config_dict[mechatronics_id]["powercurve_file"] = powercurve_file

            if mechatronics_type == "bev":
                mechatronics[mechatronics_id] = BEV.from_dict(
                    config_dict[mechatronics_id],
                    custom_powertrain_constructor,
                    custom_powercurve_constructor,
                )
            elif mechatronics_type == "ice":
                mechatronics[mechatronics_id] = ICE.from_dict(
                    config_dict[mechatronics_id], custom_powertrain_constructor
                )
            else:
                raise ValueError(
                    f"got unexpected mechatronics type {mechatronics_type}; try `bev` or `ice`"
                )

    return Map(mechatronics)
