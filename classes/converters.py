"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt
This software is dual-licensed under the GNU Affero General Public
License for non-commercial and the Travitia License for commercial
use.
For more information, see README.md and LICENSE.md.
"""

import discord
from discord.ext import commands


class NotInRange(commands.BadArgument):
    def __init__(self, text, from_, to_):
        self.text = text
        self.from_ = from_
        self.to_ = to_


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
