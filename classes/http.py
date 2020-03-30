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
from aiohttp import ClientSession as AiohttpClientSession


class ProxiedClientSession:
    """A ClientSession that forwards requests through a custom proxy."""

    def __init__(self, *args, **kwargs):
        self.proxy_url = kwargs.pop("proxy_url")

        self.permanent_headers = {
            "Proxy-Authorization-Key": kwargs.pop("authorization"),
            "Accept": "application/json",
        }
        self._session = AiohttpClientSession(*args, **kwargs)

    def get(self, url, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update(self.permanent_headers)
        headers["Requested-URI"] = url
        return self._session.get(self.proxy_url, headers=headers, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update(self.permanent_headers)
        headers["Requested-URI"] = url
        return self._session.post(self.proxy_url, headers=headers, *args, **kwargs)
