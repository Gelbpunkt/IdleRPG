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
import datetime
import re

import dateparser
import discord

from discord.ext import commands

from classes.context import Context
from utils.cache import cache
from utils.i18n import _


class MemberConverter(commands.MemberConverter):
    """Converts to a :class:`~discord.Member`.
    All lookups are via the local cache, the gateway
    and the HTTP API.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup by nickname
    Copied from https://github.com/Rapptz/discord.py/blob/sharding-rework/discord/ext/commands/converter.py
    """

    @cache(maxsize=8096)
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]+)>$", argument)
        guild = ctx.guild
        result = None
        if guild is None:
            return  # not much we can do here

        if match is None:
            # not a mention...
            match = re.match(r"(.*)#(\d{4})", argument)
            if match:
                # it is Name#0001
                name = match.group(1)
                discrim = match.group(2)
                result = discord.utils.get(
                    guild.members, name=name, discriminator=discrim
                )
                if not result:
                    members = await guild.query_members(name)
                    result = discord.utils.get(members, discriminator=discrim)
            else:
                name = argument
                discrim = None
                result = discord.utils.get(guild.members, name=name)
                if not result:
                    members = await guild.query_members(name, limit=1)
                    result = members[0]
        else:
            user_id = int(match.group(1))
            result = discord.utils.get(
                ctx.message.mentions, id=user_id
            ) or discord.utils.get(guild.members, id=user_id)
            if result is None:
                results = await guild.query_members(user_ids=[user_id], limit=1)
                if results:
                    result = results[0]

        if result is None:
            raise commands.BadArgument(f'Member "{argument}" not found')

        return result


_member_converter = MemberConverter()
_user_converter = commands.UserConverter()


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


class User(commands.UserConverter):
    @cache(maxsize=8096)
    async def convert(self, ctx: Context, argument: str) -> discord.User:
        try:
            return await _user_converter.convert(ctx, argument)
        except commands.BadArgument:
            pass

        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]+)>$", argument)
        try:
            return await ctx.bot.fetch_user(int(match.group(1)))
        except discord.NotFound:
            raise commands.BadArgument(f"User {argument} not found")


_custom_user_converter = User()


class UserWithCharacter(commands.Converter):
    async def convert(self, ctx, argument):
        user = await _custom_user_converter.convert(ctx, argument)  # error is ok here
        ctx.user_data = await ctx.bot.cache.get_profile(user.id)
        if ctx.user_data:
            return user
        else:
            raise UserHasNoChar("User has no character.", user)


class MemberWithCharacter(commands.converter.IDConverter):
    async def convert(self, ctx, argument):
        member = await _member_converter.convert(ctx, argument)  # error is ok here

        ctx.user_data = await ctx.bot.cache.get_profile(member.id)
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
    async def convert(self, ctx, arg):
        stuff = arg.lower()
        if stuff not in ["common", "uncommon", "rare", "magic", "legendary"]:
            raise InvalidCrateRarity()
        return stuff


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
        ]
        if mode not in game_modes:
            raise InvalidWerewolfMode()
        return mode
