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


def is_ken():
    def predicate(ctx):
        return ctx.author.id == 318_824_057_158_107_137

    return commands.check(predicate)


def is_shoie():
    def predicate(ctx):
        return ctx.author.id == 423425457673863179

    return commands.check(predicate)


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @locale_doc
    async def onetruechild(self, ctx):
        _("""In loving memory of Mary Johanna, ex-developer.""")
        await ctx.send(_("His name is `#no homo` :heart:"))

    @is_ken()
    @commands.command(hidden=True)
    @locale_doc
    async def ken(self, ctx, user: discord.Member):
        _("""[Ken only] Hug someone.""")
        em = discord.Embed(
            title=_("Ken Hug!"),
            description=_("{author} hugged {user}! Awww!").format(
                author=ctx.author.mention, user=user.mention
            ),
        )
        em.set_image(
            url="https://cdn.discordapp.com/attachments/515954333368713235/518539871665520641/image0.gif"  # noqa
        )
        await ctx.send(embed=em)

    @is_shoie()
    @commands.command(hidden=True)
    async def slap(self, ctx, user: discord.Member):
        """[Shoie only] Slap someone."""
        em = discord.Embed(title=f"{ctx.disp} slapped {user.display_name}").set_image(
            url="https://media.giphy.com/media/keVd9WsqHg93O/giphy.gif"
        )
        await ctx.send(embed=em)

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


def setup(bot):
    bot.add_cog(Custom(bot))
