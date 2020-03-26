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

from utils import misc as rpgtools


class Ranks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @locale_doc
    async def richest(self, ctx):
        _("""The 10 most richest players in IdleRPG.""")
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "money" FROM profile ORDER BY "money" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            text = _("{name}, a character by `{username}` with **${money}**").format(
                name=profile["name"],
                username=discord.utils.escape_markdown(username, as_needed=False),
                money=profile["money"],
            )
            result = f"{result}{idx + 1}. {text}\n"
        result = discord.Embed(
            title=_("The Richest Players"), description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(aliases=["best", "high", "top"])
    @locale_doc
    async def highscore(self, ctx):
        _("""The top 10 players by XP.""")
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "xp" from profile ORDER BY "xp" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            text = _(
                "{name}, a character by `{username}` with Level **{level}** (**{xp}** XP)"
            ).format(
                name=profile["name"],
                username=discord.utils.escape_markdown(username, as_needed=False),
                level=rpgtools.xptolevel(profile["xp"]),
                xp=profile["xp"],
            )
            result = f"{result}{idx + 1}. {text}\n"
        result = discord.Embed(
            title=_("The Best Players"), description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(aliases=["pvp", "battles"])
    @locale_doc
    async def pvpstats(self, ctx):
        _("""Top 10 players by wins in PvP matches.""")
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "name", "pvpwins" from profile ORDER BY "pvpwins" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            username = await rpgtools.lookup(self.bot, profile["user"])
            text = _("{name}, a character by `{username}` with **{wins}** wins").format(
                name=profile["name"],
                username=discord.utils.escape_markdown(username, as_needed=False),
                wins=profile["pvpwins"],
            )
            result = f"{result}{idx + 1}. {text}\n"
        result = discord.Embed(
            title=_("The Best PvPers"), description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command()
    @locale_doc
    async def lovers(self, ctx):
        _("""The top 10 lovers sorted by their spouse's lovescore.""")
        await ctx.trigger_typing()
        players = await self.bot.pool.fetch(
            'SELECT "user", "marriage", "lovescore" FROM profile ORDER BY "lovescore" DESC LIMIT 10;'
        )
        result = ""
        for idx, profile in enumerate(players):
            lovee = await rpgtools.lookup(self.bot, profile["user"])
            lover = await rpgtools.lookup(self.bot, profile["marriage"])
            text = _(
                "**{lover}** gifted their love **{lovee}** items worth **${points}**"
            ).format(
                lover=discord.utils.escape_markdown(lover, as_needed=False),
                lovee=discord.utils.escape_markdown(lovee, as_needed=False),
                points=profile["lovescore"],
            )
            result = f"{result}**{idx + 1}**. {text}\n"
        result = discord.Embed(
            title=_("The Best lovers"), description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)


def setup(bot):
    bot.add_cog(Ranks(bot))
