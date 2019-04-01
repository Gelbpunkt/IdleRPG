"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import contextlib

_sentinel = object()


@contextlib.contextmanager
def temp_attr(obj, attr, value):
    """Temporarily sets an object's attribute to a value"""
    old_value = getattr(obj, attr, _sentinel)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        if old_value is _sentinel:
            delattr(obj, attr)
        else:
            setattr(obj, attr, old_value)


# asynccontextmanager when
class temp_message:
    """Sends a temporary message, then deletes it"""

    def __init__(self, destination, content=None, *, file=None, embed=None):
        self.destination = destination
        self.content = content
        self.file = file
        self.embed = embed

    async def __aenter__(self):
        self.message = await self.destination.send(
            self.content, file=self.file, embed=self.embed
        )
        return self.message

    async def __aexit__(self, exc_type, exc, tb):
        await self.message.delete()
