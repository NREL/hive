import os
import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from nrel.hive.config.global_config import GlobalConfig
from nrel.hive.util.fs import global_hive_config_search


class TestDictReaderStepper(TestCase):
    def test_global_hive_config_search_finds_default(self):
        result = global_hive_config_search()
        self.assertIsInstance(result, GlobalConfig, "should be a GlobalConfig class instance")

    def test_global_hive_config_search_finds_parent(self):
        original_dir = os.getcwd()
        with tempfile.TemporaryDirectory() as parent:
            root_path = Path(parent)
            parent_hive_file = root_path.joinpath(".hive.yaml")
            with open(parent_hive_file, "w") as file:
                yaml.safe_dump({"log_states": False}, file)
            with tempfile.TemporaryDirectory(dir=parent) as child:
                os.chdir(child)
                result = global_hive_config_search()
                self.assertIsInstance(
                    result,
                    GlobalConfig,
                    "should be a GlobalConfig class instance",
                )
                self.assertFalse(
                    result.log_states,
                    "should have found the modified config in the parent directory",
                )  # default is "True"
                self.assertTrue(
                    result.log_run,
                    "should also contain keys from the default config",
                )
                os.chdir(original_dir)
