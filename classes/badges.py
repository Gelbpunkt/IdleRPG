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
from __future__ import annotations

from enum import IntFlag

from asyncpg.types import BitString
from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadArgument

from classes.context import Context


class Badge(IntFlag):
    CONTRIBUTOR = 1
    DESIGNER = 2
    DEVELOPER = 4
    GAME_DESIGNER = 8
    GAME_MASTER = 16
    SUPPORT = 32
    TESTER = 64
    VETERAN = 128

    @classmethod
    def from_string(cls, string: str) -> Badge | None:
        return cls.__members__.get(string.upper())

    @classmethod
    def from_db(cls, bit_string: BitString) -> Badge:
        return cls.from_bytes(bit_string.bytes, byteorder="big")

    def to_db(self) -> BitString:
        return BitString.from_int(self, 16)

    def to_items(self) -> list[str]:
        contains = []

        for (name, value) in self.__class__.__members__.items():
            if bool(self & value):
                contains.append(name)

        return contains

    def to_items_lowercase(self) -> list[str]:
        contains = []

        for (name, value) in self.__class__.__members__.items():
            if bool(self & value):
                contains.append(name.lower().replace("_", ""))

        return contains

    def to_pretty(self) -> str:
        return " | ".join(self.to_items())


class BadgeConverter(Converter[Badge]):
    async def convert(self, ctx: Context, argument: str) -> Badge:
        if (badge := Badge.from_string(argument)) is not None:
            return badge
        else:
            raise InvalidBadge()


class InvalidBadge(BadArgument):
    pass
