"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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

from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse

del ClientSession.__init_subclass__


class ProxiedClientSession(ClientSession):
    """A ClientSession that forwards requests through a custom proxy."""

    __slots__ = ("proxy_url",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.proxy_url = kwargs.pop("proxy_url")

        super().__init__(*args, **kwargs)

    async def _request(self, *args, **kwargs: Any) -> ClientResponse:
        kwargs["proxy"] = self.proxy_url
        return await super()._request(*args, **kwargs)
