"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord

from discord.ext import commands


def is_sky():
    def predicate(ctx):
        return ctx.author.id == 201_873_056_967_163_904

    return commands.check(predicate)


def is_ken():
    def predicate(ctx):
        return ctx.author.id == 318_824_057_158_107_137

    return commands.check(predicate)


class Custom:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="TNG!", hidden=True)
    async def tng(self, ctx):
        await ctx.send(file=discord.File("custom/tng.jpg"))

    @is_sky()
    @commands.command(description="Gives a rainbow cookie to a user!", hidden=True)
    async def rainbowcookie(self, ctx, user: discord.Member):
        await ctx.send(
            f"**{user.display_name}**, you have been awarded a 🌈 🍪 🌈"
            f"by **{ctx.author.display_name}**!"
        )

    @is_ken()
    @commands.command(description="Hug someone!", hidden=True)
    async def ken(self, ctx, user: discord.Member):
        em = discord.Embed(
            title="Ken Hug!",
            description=f"{ctx.author.mention} hugged {user.mention}! Awww!",
        )
        em.set_image(
            url="https://cdn.discordapp.com/attachments/515954333368713235/518539871665520641/image0.gif"  # noqa
        )
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Custom(bot))
