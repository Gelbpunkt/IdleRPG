"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import discord
from discord.ext import commands

from utils import misc as rpgtools


class Ranks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def richest(self, ctx):
        """The 10 richest players."""
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "money" FROM profile ORDER BY "money" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            result = f"{result}{idx + 1}. {profile['name']}, a character by `{username}` with **${profile['money']}**\n"
        result = discord.Embed(
            title="The Richest Players", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(aliases=["best", "high", "top"])
    async def highscore(self, ctx):
        """The top 10 players by XP."""
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "xp" from profile ORDER BY "xp" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            result = f"{result}{idx + 1}. {profile['name']}, a character by `{username}` with Level **{rpgtools.xptolevel(profile['xp'])}** (**{profile['xp']}** XP)\n"
        result = discord.Embed(
            title="The Best Players", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(aliases=["pvp", "battles"],)
    async def pvpstats(self, ctx):
        """Top 10 players by wins in PvP matches."""
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "pvpwins" from profile ORDER BY "pvpwins" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            result = f"{result}{idx + 1}. {profile['name']}, a character by `{username}` with **{profile['pvpwins']}** wins\n"
        result = discord.Embed(
            title="The Best PvPers", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command()
    async def lovers(self, ctx):
        """The top 10 lovers sorted by their spouse's lovescore."""
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "marriage", "lovescore" FROM profile ORDER BY "lovescore" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            lovee = await rpgtools.lookup(self.bot, profile["user"])
            lover = await rpgtools.lookup(self.bot, profile["marriage"])
            result = f"{result}**{idx + 1}**. **{lover}** gifted their love **{lovee}** items worth **${profile['lovescore']}**\n"
        result = discord.Embed(
            title="The Best lovers", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)


def setup(bot):
    bot.add_cog(Ranks(bot))
