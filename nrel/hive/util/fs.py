from pathlib import Path
from typing import Optional, Union

import pkg_resources
import yaml

from nrel.hive.config.global_config import GlobalConfig


def global_hive_config_search() -> GlobalConfig:
    """
    searches for the global hive config, and if found, loads it. if not, loads the default from nrel.hive.resources
    :return: global hive config
    """

    # this searches up the path to the root of the file system
    def _backprop_search(search_path: Path) -> Optional[Path]:
        try:
            search_file = search_path.joinpath(".hive.yaml")
            if search_file.is_file():
                return search_file
            else:
                updated_search_path = search_path.parent
                if updated_search_path == search_path:
                    return None
                else:
                    return _backprop_search(updated_search_path)
        except FileNotFoundError:
            return None

    # load the default file to be merged with any found files
    default_global_config_file_path = pkg_resources.resource_filename(
        "nrel.hive.resources.defaults", ".hive.yaml"
    )
    with Path(default_global_config_file_path).open() as df:
        default = yaml.safe_load(df)

    # search up the directory tree for a config file
    try:
        cwd = Path.cwd()
    except FileNotFoundError:
        cwd = Path("~/")

    file_found_in_backprop = _backprop_search(cwd)

    # check user home directory for a config file
    file_at_home_directory = Path.home().joinpath(".hive.yaml")
    file_found_at_home_directory = file_at_home_directory.is_file()

    # if we found a file (preferring the ones in the directory tree over the user home directory), we use that
    file_found = (
        file_found_in_backprop
        if file_found_in_backprop
        else file_at_home_directory
        if file_found_at_home_directory
        else None
    )
    if file_found:
        with file_found.open() as f:
            global_hive_config = yaml.safe_load(f)
            default.update(global_hive_config)
            return GlobalConfig.from_dict(default, str(file_found))
    else:
        return GlobalConfig.from_dict(default, default_global_config_file_path)


def construct_asset_path(
    file: Union[str, Path],
    scenario_directory: Union[str, Path],
    default_directory_name: str,
    resources_subdirectory: str,
) -> str:
    """
    constructs the path to a scenario asset relative to a scenario directory. attempts to load at both
    the user-provided relative path, and if that fails, attempts to load at the default directory; finally, checks
    the resources directory for a fallback.

    for example, with file "leaf.yaml", scenario_directory "/home/jimbob/hive/denver" and default_directory "powertrain",
    this will test "/home/jimbob/hive/denver/leaf.yaml" then "/home/jimbob/hive/denver/vehicles/leaf.yaml" and finally
    "hive/resources/powertrain/leaf.yaml" and return the first path where the file is found to exist.


    :param file: file we are seaching for
    :param scenario_directory: the scenario directory
    :param default_directory_name: the directory name where assets of this type are typically saved
    :param resources_subdirectory: the subdirectory of resources where we also expect this could be saved
    :return: the path string if the file exists, otherwise None
    :raises: FileNotFoundError if asset is not found
    """
    file = Path(file)
    try:
        result = construct_scenario_asset_path(file, scenario_directory, default_directory_name)
        return result
    except FileNotFoundError:
        # try the resources directory fallback
        fallback = pkg_resources.resource_filename(
            f"nrel.hive.resources.{resources_subdirectory}", str(file)
        )
        if Path(fallback).is_file():
            return fallback
        else:
            msg = (
                f"could not find the file {file} in any of the following locations: \n"
                f" - {Path(scenario_directory).joinpath(file)} \n"
                f" - {Path(scenario_directory).joinpath(default_directory_name).joinpath(file)} \n"
                f" - {Path(fallback)}"
            )

            raise FileNotFoundError(msg)


def construct_scenario_asset_path(
    file: Union[str, Path], scenario_directory: Union[str, Path], default_directory_name: str
) -> str:
    """
    constructs the path to a scenario asset relative to a scenario directory. attempts to load at both
    the user-provided relative path, and if that fails, attempts to load at the default directory.

    for example, with file "vehicles.csv", scenario_directory "/home/jimbob/hive/denver" and default_directory "vehicles",
    this will test "/home/jimbob/hive/denver/vehicles.csv" then "/home/jimbob/hive/denver/vehicles/vehicles.csv" and return
    the first path where the file is found to exist.


    :param file: file we are searching for
    :param scenario_directory: the directory where the scenario file was found
    :param default_directory_name: the default directory name for the type of asset we are checking for
    :return: the path string if the file exists, otherwise None
    :raises: FileNotFoundError if asset is not found
    """
    file_at_scenario_directory = Path(scenario_directory).joinpath(file)
    file_at_default_directory = (
        Path(scenario_directory).joinpath(default_directory_name).joinpath(file)
    )
    if file_at_scenario_directory.is_file():
        return str(file_at_scenario_directory)
    elif file_at_default_directory.is_file():
        return str(file_at_default_directory)
    else:
        raise FileNotFoundError(f"cannot find file {file} in directory {scenario_directory}")


def find_scenario(user_provided_scenario: str) -> Path:
    """
    allows users to declare built-in scenario filenames without absolute/relative paths or
    expects the user has provided a valid relative/absolute to another file


    :param user_provided_scenario: the scenario requested
    :return: the absolute path of this scenario if it exists
    :raises: FileNotFoundError
    """
    absolute_path = Path(user_provided_scenario).absolute()
    relative_path = Path.cwd().joinpath(user_provided_scenario)
    den_path = Path(
        pkg_resources.resource_filename(
            "nrel.hive.resources.scenarios.denver_downtown",
            user_provided_scenario,
        )
    )
    nyc_path = Path(
        pkg_resources.resource_filename(
            "nrel.hive.resources.scenarios.manhattan", user_provided_scenario
        )
    )

    print(den_path)

    if absolute_path.is_file():
        return absolute_path
    elif relative_path.is_file():
        return relative_path
    elif den_path.is_file():
        return den_path
    elif nyc_path.is_file():
        return nyc_path
    else:
        raise FileNotFoundError(user_provided_scenario)
