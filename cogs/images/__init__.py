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
import discord

from discord.ext import commands
from discord.ext.commands import BucketType

from utils.i18n import _, locale_doc


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=_("Pixelfy an avatar"))
    @locale_doc
    async def pixelfy(self, ctx, user: discord.Member = None, size: int = 2):
        _(
            """`[user]` - A discord User whose avatar to pixelfy; defaults to oneself
            `[size]` - The pixelation rate to use, can be a number between 1 and 5; defaults to 2

            Pixelfies a user's avatar. If the user has an animated icon, the first frame is used."""
        )
        user = user or ctx.author
        try:
            size = [256, 128, 64, 32, 16][size - 1]
        except IndexError:
            return await ctx.send(_("Use 1, 2, 3, 4 or 5 as intensity value."))
        url = user.display_avatar.replace(format="png", size=size).url
        # change size to lower for less pixels
        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/imageops/pixel",
            json={"image": url},
            headers={"Authorization": self.bot.config.external.okapi_token},
        ) as r:
            image = await r.text()
        await ctx.send(
            embed=discord.Embed(color=discord.Colour.blurple()).set_image(url=image)
        )

    @commands.command(brief=_("Defines an avatar's edges"))
    @locale_doc
    async def edgy(self, ctx, user: discord.Member = None):
        _(
            """`[user]` - A discord User whose avatar to edit; defaults to oneself

            Finds and exaggerates edges in a user's avatar, creating a cool image effect."""
        )
        user = user or ctx.author
        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/imageops/edges",
            json={"image": user.display_avatar.replace(format="png").url},
            headers={"Authorization": self.bot.config.external.okapi_token},
        ) as r:
            image = await r.text()
        await ctx.send(
            embed=discord.Embed(color=discord.Colour.blurple()).set_image(url=image)
        )

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command(brief=_("Inverts a user's avatar"))
    @locale_doc
    async def invert(self, ctx, user: discord.Member = None):
        _(
            """`[user]` - A discord User whose avatar to invert; defaults to oneself

            Invert the colors in someone's avatar.

            (This command has a channel cooldown of 15 seconds.)"""
        )
        user = user or ctx.author
        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/imageops/invert",
            json={"image": user.display_avatar.replace(format="png").url},
            headers={"Authorization": self.bot.config.external.okapi_token},
        ) as r:
            image = await r.text()
        await ctx.send(
            embed=discord.Embed(color=discord.Colour.blurple()).set_image(url=image)
        )

    @commands.cooldown(1, 15, BucketType.channel)
    @commands.command(brief=_("Oil-paint someone's avatar"))
    @locale_doc
    async def oil(self, ctx, user: discord.Member = None):
        _(
            """`[user]` - A discord User whose avatar to oil-paint; defaults to oneself

            Creates an oil-painting effect on someone's avatar.

            (This command has a channel cooldown of 15 seconds.)"""
        )
        user = user or ctx.author
        async with self.bot.trusted_session.post(
            f"{self.bot.config.external.okapi_url}/api/imageops/oil",
            json={"image": user.display_avatar.replace(format="png").url},
            headers={"Authorization": self.bot.config.external.okapi_token},
        ) as r:
            image = await r.text()
        await ctx.send(
            embed=discord.Embed(color=discord.Colour.blurple()).set_image(url=image)
        )


def setup(bot):
    bot.add_cog(Images(bot))
