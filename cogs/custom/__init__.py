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
import discord

from discord.ext import commands


def is_meliodas():
    def predicate(ctx):
        return ctx.author.id == 150323474014011399

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

    @is_meliodas()
    @commands.command(hidden=True)
    async def meliodas(self, ctx):
        """Will he lose his money?"""
        msg = await ctx.send("Will Meliodas lose all his money today?")
        await msg.add_reaction("\U00002705")
        await msg.add_reaction("\U0000274e")

    @is_zinquo()
    @commands.command(hidden=True)
    async def phoenix(self, ctx):
        """Temporary placeholder."""
        await ctx.send(
            "> “When the bones settle and all the ash falls, the phoenix will be reborn, and life begins anew.”"
        )


def setup(bot):
    bot.add_cog(Custom(bot))
