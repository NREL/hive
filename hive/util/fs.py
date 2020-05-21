import os
from typing import Optional
from pathlib import Path
from hive.config import GlobalConfig
import pkg_resources
import yaml


def global_hive_config_search() -> GlobalConfig:
    """
    searches for the global hive config, and if found, loads it. if not, loads the default from hive.resources
    :return: global hive config
    """
    # this searches up the path to the root of the file system
    def _backprop_search(search_path: Path) -> Optional[Path]:
        search_file = search_path.joinpath(".hive.yaml")
        if search_file.is_file():
            return search_file
        else:
            updated_search_path = search_path.parent
            if updated_search_path == search_path:
                return None
            else:
                return _backprop_search(updated_search_path)

    # load the default file to be merged with any found files
    with Path(pkg_resources.resource_filename("hive.resources.defaults", ".hive.yaml")).open() as df:
        default = yaml.safe_load(df)

    file_found_in_backprop = _backprop_search(Path.cwd())
    file_at_home_directory = Path.home().joinpath(".hive.yaml")
    file_found_at_home_directory = file_at_home_directory.is_file()
    file_found = file_found_in_backprop if file_found_in_backprop else file_at_home_directory if file_found_at_home_directory else None
    if file_found:
        with file_found.open() as f:
            global_hive_config = yaml.safe_load(f)
            default.update(global_hive_config)
            return GlobalConfig.from_dict(default)
    else:
        return GlobalConfig.from_dict(default)


def search_for_file(file: str, scenario_directory: str, data_directory: Optional[str] = None) -> Optional[str]:
    """
    returns a URI to a file, attempting to find the file at
    1. the scenario directory, where the path is relative to the user-defined data directory
    2. the scenario directory, where the path is absolute
    3. the scenario directory, where the path is relative to the current working directory
    4. the hive.resources package as a fallback
    :param file: the filename we are looking for
    :param scenario_directory: the input directory set in the scenario config
    :param data_directory: the user's global data directory location, or None if not defined
    :return: the complete URI to the file if it was found, otherwise None
    """

    file_at_data_dir_plus_input_dir = os.path.normpath(os.path.join(data_directory, scenario_directory, file)) if data_directory else None
    file_at_input_dir = os.path.normpath(os.path.join(scenario_directory, file))
    file_at_cwd_plus_input_dir = os.path.normpath(os.path.join(os.getcwd(), scenario_directory, file))
    file_at_resources_dir = pkg_resources.resource_filename("hive.resources", file)

    if file_at_data_dir_plus_input_dir and os.path.isfile(file_at_data_dir_plus_input_dir):
        return file_at_data_dir_plus_input_dir
    elif os.path.isfile(file_at_input_dir):
        return file_at_input_dir
    elif os.path.isfile(file_at_cwd_plus_input_dir):
        return file_at_cwd_plus_input_dir
    elif os.path.isfile(file_at_resources_dir):
        return file_at_resources_dir
    else:
        return None
