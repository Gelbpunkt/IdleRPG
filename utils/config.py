import toml
from typing import Optional, Any


class ConfigLoader:
    """ConfigLoader provides methods for loading and reading values from a .toml file."""
    __slots__ = {'config', 'values'}

    def __init__(self, path: str):
        # the path to the config file of this loader
        self.config = path
        # values initialized as empty dict, in case loading fails
        self.values = {}
        self.reload()

    def get_config_value(self, *keys: str) -> Optional[Any]:
        """Get the value of a certain key in this config. Additional keys will get nested elements.
        Returns the found dict or element, if any.
        """
        value = self.values
        for k in keys:
            try:
                value = value[k]
            except KeyError:
                return None
        return value

    def reload(self) -> None:
        """Loads the config using the path this loader was initialized with, overriding any previously stored values."""
        self.values = toml.load(self.config)
