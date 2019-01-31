import discord
from discord.ext import commands
from utils import misc as rpgtools


class Ranks:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Shows the richest players. Maximum 10.")
    async def richest(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                """
                SELECT "user", "name", "money"
                FROM profile
                ORDER BY "money" DESC
                LIMIT 10;'
            """
            )
        if ret == []:
            return await ctx.send(
                "No character have been created yet. Use `{ctx.prefix}create` to be the first one!"
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            charname = await rpgtools.lookup(self.bot, profile[0])
            pstring = f"{number}. {profile[1]}, a character by `{charname}` with **${profile[2]}**\n"
            result += pstring
        result = discord.Embed(
            title="The Richest Players", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(
        aliases=["best", "high", "top"],
        description="Shows the best players sorted by XP. Maximum 10.",
    )
    async def highscore(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT "user", "name", "xp" from profile ORDER BY "xp" DESC LIMIT 10;'
            )
        if ret == []:
            return await ctx.send(
                "No character have been created yet. Use `{ctx.prefix}create` to be the first one!"
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            charname = await rpgtools.lookup(self.bot, profile[0])
            pstring = f"{number}. {profile[1]}, a character by `{charname}` with Level **{rpgtools.xptolevel(profile[2])}** (**{profile[2]}** XP)\n"
            result += pstring
        result = discord.Embed(
            title="The Best Players", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(
        aliases=["pvp", "battles"],
        description="Shows the best PvP players. Maximum 10.",
    )
    async def pvpstats(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT "user", "name", "pvpwins" from profile ORDER BY "pvpwins" DESC LIMIT 10;'
            )
        if ret == []:
            return await ctx.send(
                "No character have been created yet. Use `{ctx.prefix}create` to be the first one!"
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            charname = await rpgtools.lookup(self.bot, profile[0])
            pstring = f"{number}. {profile[1]}, a character by `{charname}` with **{profile[2]}** wins\n"
            result += pstring
        result = discord.Embed(
            title="The Best PvPers", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)

    @commands.command(description="Shows the best lovers.")
    async def lovers(self, ctx):
        await ctx.trigger_typing()
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT "user", "marriage", "lovescore" FROM profile ORDER BY "lovescore" DESC LIMIT 10;'
            )
        if ret == []:
            return await ctx.send(
                "No character have been created yet. Use `{ctx.prefix}create` to be the first one!"
            )
        result = ""
        for profile in ret:
            number = ret.index(profile) + 1
            user = await rpgtools.lookup(self.bot, profile[0])
            lover = await rpgtools.lookup(self.bot, profile[1])
            result += f"**{number}**. **{lover}** gifted their love **{user}** items worth **${profile[2]}**\n"
        result = discord.Embed(
            title="The Best lovers", description=result, colour=0xE7CA01
        )
        await ctx.send(embed=result)


def setup(bot):
    bot.add_cog(Ranks(bot))
