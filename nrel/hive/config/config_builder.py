from __future__ import annotations

from typing import *


class ConfigBuilder:
    T = TypeVar("T")

    @classmethod
    def build(
        cls,
        default_config: Dict,
        required_config: Tuple[str, ...],
        config_constructor: Callable[[Dict], T],
        config: Optional[Dict] = None,
    ) -> T:
        """
        constructs a Config from a configuration Dict

        :param default_config: a dictionary containing default config values
        :param required_config: a dictionary containing required keys and their expected types
        :param config_constructor: a function that takes a dict and builds a Config object
        :param config: the Dict containing attributes to load for this Config
        :return: a Config, or, an error
        """

        c = (
            default_config
            if config is None
            else dict(list(default_config.items()) + list(config.items()))
        )
        for key in required_config:
            value = c.get(key)
            if value is None:
                raise AttributeError(f"expected required config key {key} not found")

        return config_constructor(c)
