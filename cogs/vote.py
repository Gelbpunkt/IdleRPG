"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


from discord.ext import commands


class Vote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Sends a vote link.")
    async def vote(self, ctx):
        await ctx.send(
            "Upvote me for a big thanks! You will be rewarded a few seconds afterwards!\nhttps://discordbots.org/bot/idlerpg"
        )


def setup(bot):
    bot.add_cog(Vote(bot))
