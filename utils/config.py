"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from typing import Any

import toml


class ConfigLoader:
    """ConfigLoader provides methods for loading and reading values from a .toml file."""

    __slots__ = {"config", "values"}

    def __init__(self, path: str) -> None:
        # the path to the config file of this loader
        self.config = path
        # values initialized as empty dict, in case loading fails
        self.values = {}
        self.reload()

    def get_config_value_with_default(self, *keys: str, **kwargs: Any) -> Any:
        """Get the value of a certain key in this config. Additional keys will get nested elements.
        Returns the found dict or element, if any.
        """
        value = self.values
        default = kwargs.pop("default", None)
        for k in keys:
            try:
                value = value[k]
            except KeyError:
                if isinstance(default, Exception):
                    raise default
                else:
                    return default
        return value

    def get_config_value(self, *keys: str) -> Any:
        return self.get_config_value_with_default(*keys)

    def get_config_value_or_err(self, *keys: str, **kwargs: Any) -> Any:
        return self.get_config_value_with_default(
            *keys, default=kwargs.pop("error", KeyError)
        )

    def reload(self) -> None:
        """Loads the config using the path this loader was initialized with, overriding any previously stored values."""
        self.values = toml.load(self.config)
