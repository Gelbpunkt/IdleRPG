"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

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
from io import BytesIO

import discord

from discord.ext import commands
from discord.ext.commands import BucketType
from discord.ext.commands.default import Author


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @locale_doc
    async def pixelfy(self, ctx, user: discord.Member = Author, size: int = 2):
        _("""Pixelfys an Avatar.""")
        try:
            size = [256, 128, 64, 32, 16][size - 1]
        except IndexError:
            return await ctx.send(_("Use 1, 2, 3, 4 or 5 as intensity value."))
        url = str(user.avatar_url_as(format="png", size=size))
        # change size to lower for less pixels
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/imageops/pixel", data={"image": url}
        ) as r:
            img = BytesIO(await r.read())
        await ctx.send(file=discord.File(fp=img, filename="pixels.png"))

    @commands.command()
    @locale_doc
    async def edgy(self, ctx, user: discord.Member = Author):
        _("""Finds edges in an Avatar.""")
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/imageops/edges",
            data={"image": str(user.avatar_url_as(format="webp"))},
        ) as r:
            img = BytesIO(await r.read())
        await ctx.send(file=discord.File(fp=img, filename="edgy.png"))

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command()
    @locale_doc
    async def invert(self, ctx, member: discord.Member = Author):
        _("""Inverts an avatar.""")
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/imageops/invert",
            data={"image": str(member.avatar_url_as(format="webp"))},
        ) as r:
            img = BytesIO(await r.read())
        await ctx.send(file=discord.File(fp=img, filename="inverted.png"))

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command()
    @locale_doc
    async def oil(self, ctx, member: discord.Member = Author):
        _("""Oils an Avatar.""")
        async with self.bot.trusted_session.post(
            f"{self.bot.config.okapi_url}/api/imageops/oil",
            data={"image": str(member.avatar_url_as(format="png"))},
        ) as r:
            img = BytesIO(await r.read())

        await ctx.send(file=discord.File(fp=img, filename="oil.png"))


def setup(bot):
    bot.add_cog(Images(bot))
