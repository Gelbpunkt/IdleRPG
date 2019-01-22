import discord
from discord.ext import commands


class Ranked:
    pass


def setup(bot):
    bot.add_cog(Ranked(bot))
