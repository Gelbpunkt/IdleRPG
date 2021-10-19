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

from aiohttp.client import ClientSession, _RequestContextManager
from multidict import MultiDict
from yarl import URL


class ProxiedClientSession:
    """A ClientSession that forwards requests through a custom proxy."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.proxy_url = kwargs.pop("proxy_url")

        self.permanent_headers = {
            "Proxy-Authorization-Key": kwargs.pop("authorization"),
            "Accept": "application/json",
        }
        self._session = ClientSession(*args, **kwargs)

    def get(self, url: str, *args: Any, **kwargs: Any) -> _RequestContextManager:
        params = kwargs.pop("params", {})
        if params:
            request_url = URL(url)
            q = MultiDict(request_url.query)
            url2 = request_url.with_query(params)
            q.extend(url2.query)
            request_url = request_url.with_query(q)
            url = str(request_url)

        headers = kwargs.pop("headers", {})
        headers.update(self.permanent_headers)
        headers["Requested-URI"] = url

        return self._session.get(self.proxy_url, headers=headers, *args, **kwargs)

    def post(self, url: str, *args: Any, **kwargs: Any) -> _RequestContextManager:
        params = kwargs.pop("params", {})
        if params:
            request_url = URL(url)
            q = MultiDict(request_url.query)
            url2 = request_url.with_query(params)
            q.extend(url2.query)
            request_url = request_url.with_query(q)
            url = str(request_url)

        headers = kwargs.pop("headers", {})
        headers.update(self.permanent_headers)
        headers["Requested-URI"] = url
        return self._session.post(self.proxy_url, headers=headers, *args, **kwargs)
