from __future__ import annotations
from typing import *


class ConfigBuilder:

    T = TypeVar('T')

    @classmethod
    def build(cls,
              default_config: Dict,
              required_config: Dict[str, type],
              config_constructor: Callable[[Dict], Union[Exception, T]],
              config: Dict = None) -> T:
        """
        constructs a Config from a configuration Dict
        :param default_config: a dictionary containing default config values
        :param required_config: a dictionary containing required keys and their expected types
        :param config_constructor: a function that takes a dict and builds a Config object
        :param config: the Dict containing attributes to load for this Config
        :return: a Config, or, an error
        """

        c = default_config if config is None else dict(list(default_config.items()) + list(config.items()))
        for key, key_type in required_config.items():
            value = c.get(key)
            if value is None:
                raise AttributeError(f"expected required config key {key} of type {key_type} not found")
            elif type(key_type) is tuple:
                if all(not isinstance(value, kt) for kt in key_type):
                    raise AttributeError(f"value {value} at config key {key} not correct type {key_type}")
            elif not isinstance(value, key_type):
                raise AttributeError(f"value {value} at config key {key} not correct type {key_type}")

        return config_constructor(c)
