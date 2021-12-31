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
import datetime

from enum import Flag

import dateparser

from discord.ext import commands
from yarl import URL

from utils.i18n import _


class NotInRange(commands.BadArgument):
    def __init__(self, text: str, from_: int, to_: int) -> None:
        self.text = text
        self.from_ = from_
        self.to_ = to_


class InvalidCrateRarity(commands.BadArgument):
    pass


class InvalidCoinSide(commands.BadArgument):
    pass


class UserHasNoChar(commands.BadArgument):
    pass


class DateOutOfRange(commands.BadArgument):
    def __init__(self, min_: datetime.datetime) -> None:
        self.min_ = min_


class InvalidTime(commands.BadArgument):
    def __init__(self, text: str) -> None:
        self.text = text


class InvalidWerewolfMode(commands.BadArgument):
    pass


class InvalidUrl(commands.BadArgument):
    pass


class UserWithCharacter(commands.UserConverter):
    async def convert(self, ctx, argument):
        user = await super().convert(ctx, argument)  # error is ok here
        ctx.user_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', user.id
        )
        if ctx.user_data:
            return user
        else:
            raise UserHasNoChar("User has no character.", user)


class MemberWithCharacter(commands.MemberConverter):
    async def convert(self, ctx, argument):
        member = await super().convert(ctx, argument)  # error is ok here

        ctx.user_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', member.id
        )
        if ctx.user_data:
            return member
        else:
            raise UserHasNoChar("User has no character.", member)


class IntFromTo(commands.Converter):
    def __init__(self, from_, to_):
        self.from_ = from_
        self.to_ = to_

    async def convert(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            raise commands.BadArgument("Converting to int failed.")
        if not self.from_ <= arg <= self.to_:
            raise NotInRange(
                _("The supplied number must be in range of {from_} to {to_}.").format(
                    from_=self.from_, to_=self.to_
                ),
                self.from_,
                self.to_,
            )
        return arg


class IntGreaterThan(commands.Converter):
    def __init__(self, min_):
        self.min_ = min_

    async def convert(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            raise commands.BadArgument("Converting to int failed.")
        if not self.min_ < arg:
            raise NotInRange(
                ("The supplied number must be greater than {min_}.").format(
                    min_=self.min_
                ),
                self.min_ + 1,
                "infinity",
            )
        return arg


class CrateRarity(commands.Converter):
    async def convert(self, ctx, arg) -> str:
        stuff = arg.lower()
        rarities = {
            "c": "common",
            "u": "uncommon",
            "r": "rare",
            "m": "magic",
            "l": "legendary",
            "myst": "mystery",
        }
        rarity = rarities.get(stuff, stuff)
        if rarity not in rarities.values():
            raise InvalidCrateRarity()
        return rarity


class CoinSide(commands.Converter):
    async def convert(self, ctx, arg):
        stuff = arg.lower()
        if stuff not in ["heads", "tails"]:
            raise InvalidCoinSide()
        return stuff


class DateNewerThan(commands.Converter):
    def __init__(self, min_date):
        self.min_date = min_date

    async def convert(self, ctx, date_info):
        try:
            date = dateparser.parse(date_info)
            date = date.date()
        except (ValueError, AttributeError):
            raise commands.BadArgument()
        if date < self.min_date or date > datetime.date.today():
            raise DateOutOfRange(self.min_date)
        return date


def parse_date(date_string):
    return dateparser.parse(
        date_string,
        settings={
            "TO_TIMEZONE": "UTC",
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
        languages=["en"],
    )


class DateTimeScheduler(commands.Converter):
    async def convert(self, ctx, content):
        if content.startswith("me"):
            content = content.replace("me", "", 1).strip()
            # catches "remind me"
        if time := parse_date(content):
            subject = _("something")
        else:
            stuff = content.split()
            worked = False
            for i in range(len(stuff) - 1, -1, -1):
                time, subject = " ".join(stuff[:i]), " ".join(stuff[i:])
                if time := parse_date(time):
                    worked = True
                    break
            if not worked:
                raise InvalidTime(_("Could not determine a time from this."))
        if time < datetime.datetime.utcnow():
            raise InvalidTime(_("That time is in the past."))
        return time + datetime.timedelta(seconds=1), subject


class WerewolfMode(commands.Converter):
    async def convert(self, ctx, arg):
        mode = arg.title()
        game_modes = [
            "Classic",
            "Imbalanced",
            "Huntergame",
            "Villagergame",
            "Valentines",
            "Idlerpg",
        ]
        if mode not in game_modes:
            raise InvalidWerewolfMode()
        return mode


class ImageFormat(Flag):
    png = 1
    jpg = 2
    jpeg = 2
    webp = 4
    all_static = 7
    gif = 8
    all = 15


class ImageUrl(commands.Converter):
    def __init__(self, valid_types: ImageFormat = None):
        self.valid_types = valid_types

    async def convert(self, ctx, passed_url, *, silent: bool = False):
        url = URL(passed_url)
        if not all(
            [
                url.scheme,  # http, https, etc.
                url.host,  # i.imgur.com
                url.path,  # 123abc.png
            ]
        ):
            if silent:
                return None
            else:
                raise InvalidUrl()

        if self.valid_types:
            file_type = url.parts[-1].split(".")[-1]  # this ignores ?height=x&width=y
            try:
                if not (ImageFormat[file_type] & self.valid_types).value > 0:
                    raise ValueError
            except (ValueError, KeyError):
                if silent:
                    return None
                else:
                    raise InvalidUrl()

        return str(url)
