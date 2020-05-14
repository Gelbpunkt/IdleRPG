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
import discord

from discord.ext import commands

from utils import random
from utils.i18n import _, locale_doc


def is_starlit():
    def predicate(ctx):
        return ctx.author.id == 549379625587834898

    return commands.check(predicate)


def is_zinquo():
    def predicate(ctx):
        return ctx.author.id == 189929542465355776

    return commands.check(predicate)


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @locale_doc
    async def onetruechild(self, ctx):
        _("""In loving memory of Mary Johanna, ex-developer.""")
        await ctx.send(_("His name is `#no homo` :heart:"))

    @commands.command(hidden=True)
    @locale_doc
    async def jester(self, ctx):
        _("""Use to have Jester cast a spell ✨""")
        await ctx.send(
            random.choice(
                [
                    _(
                        "Jester casts Spirit Guardians on herself. She, and the"
                        " spiritual hamster unicorns have a dance party."
                    ),
                    _(
                        "Jester casts Spiritual Weapon. A comically large spectral"
                        " lollipop🍭 suddenly appears."
                    ),
                    _(
                        "Jester casts Invoke Duplicity.... Now there's twice the Jester"
                        " for twice the pranks!"
                    ),
                ]
            )
        )

    @commands.command()
    @locale_doc
    async def secret(self, ctx):
        _("""It's a secret.""")
        await ctx.send(
            embed=discord.Embed(
                title=_("Gotcha"), description=_("Shhh, it's a secret!")
            ).set_image(
                url="https://cdn.discordapp.com/attachments/571201192382693376/613965413801263104/image0.jpg"
            ),
            delete_after=3,
        )

    @commands.command(hidden=True)
    async def kill(self, ctx, target: discord.Member):
        """Kill someone."""
        await ctx.send(
            embed=discord.Embed(
                title=f"{target} has been killed by {ctx.author}."
            ).set_image(
                url="https://media.discordapp.net/attachments/439779845673844739/625403834033766428/kill.gif"
            )
        )

    @is_zinquo()
    @commands.command(hidden=True)
    async def phoenix(self, ctx):
        """Temporary placeholder."""
        await ctx.send(
            "> “When the bones settle and all the ash falls, the phoenix will be"
            " reborn, and life begins anew.”"
        )

    @is_starlit()
    @commands.command(hidden=True)
    async def lick(self, ctx, *, user: discord.Member):
        """Get someone in sick and loving way."""
        await ctx.send(
            embed=discord.Embed(
                title=f"{ctx.author} licks {user}!", colour=ctx.author.colour
            ).set_image(
                url=random.choice(
                    [
                        "https://i.imgur.com/LiLbLw0.gif",
                        "https://i.imgur.com/9tU0AFl.gif",
                    ]
                )
            )
        )


def setup(bot):
    bot.add_cog(Custom(bot))
