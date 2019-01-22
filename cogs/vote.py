import discord, aiohttp, random
from discord.ext import commands
from discord.ext.commands import BucketType


class Vote:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Sends a vote link.")
    async def vote(self, ctx):
        await ctx.send(
            f"Upvote me for a big thanks! You will be rewarded a few seconds afterwards!\nhttps://discordbots.org/bot/idlerpg"
        )


def setup(bot):
    bot.add_cog(Vote(bot))
