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
