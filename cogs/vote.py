from discord.ext import commands


class Vote:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Sends a vote link.")
    async def vote(self, ctx):
        await ctx.send(
            f"""
            Upvote me for a big thanks! You will be rewarded a few seconds afterwards!
            https://discordbots.org/bot/idlerpg"
        """
        )


def setup(bot):
    bot.add_cog(Vote(bot))
