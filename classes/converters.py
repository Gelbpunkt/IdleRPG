"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public
License for non-commercial and the Travitia License for commercial
use.
For more information, see README.md and LICENSE.md.
"""
import re

import discord
from discord.ext import commands


class NotInRange(commands.BadArgument):
    def __init__(self, text, from_, to_):
        self.text = text
        self.from_ = from_
        self.to_ = to_


class InvalidCrateRarity(commands.BadArgument):
    pass


class InvalidCoinSide(commands.BadArgument):
    pass


class UserHasNoChar(commands.BadArgument):
    pass


class User(commands.Converter):
    async def convert(self, ctx, argument):
        # TODO: Try the local users first
        data = await ctx.bot.cogs["Sharding"].handler(
            "fetch_user", 1, {"user_inp": argument}
        )
        if not data:
            raise commands.BadArgument(ctx.message, argument)
        data = data[0]
        data["username"] = data["name"]
        user = discord.User(state=ctx.bot._connection, data=data)
        ctx.bot.users.append(user)
        return user


class UserWithCharacter(commands.Converter):
    async def convert(self, ctx, argument):
        # TODO: Try the local users first
        data = await ctx.bot.cogs["Sharding"].handler(
            "fetch_user", 1, {"user_inp": argument}
        )
        if not data:
            raise commands.BadArgument("Unknown user.", argument)
        data = data[0]
        data["username"] = data["name"]
        user = discord.User(state=ctx.bot._connection, data=data)
        ctx.bot.users.append(user)
        ctx.user_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', user.id
        )
        if ctx.user_data:
            return user
        else:
            raise UserHasNoChar("User has no character.", user)


class MemberWithCharacter(commands.converter.IDConverter):
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]+)>$", argument)
        result = None
        if match is None:
            # not a mention...
            if ctx.guild:
                result = ctx.guild.get_member_named(argument)
            else:
                result = commands.converter._get_from_guilds(
                    ctx.bot, "get_member_named", argument
                )
        else:
            user_id = int(match.group(1))
            if ctx.guild:
                result = ctx.guild.get_member(user_id)
            else:
                result = commands.converter._get_from_guilds(
                    ctx.bot, "get_member", user_id
                )

        if result is None:
            raise commands.BadArgument(f"Member '{argument}' not found")

        ctx.user_data = await ctx.bot.pool.fetchrow(
            'SELECT * FROM profile WHERE "user"=$1;', result.id
        )
        if ctx.user_data:
            return result
        else:
            raise UserHasNoChar("User has no character.", result)


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
                f"The supplied number must be in range of {self.from_} to {self.to_}.",
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
                f"The supplied number must be greater than {self.min_}.",
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
