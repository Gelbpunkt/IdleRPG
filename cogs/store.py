"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import discord
from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan
from utils.checks import has_char


class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def store(self, ctx):
        """The booster store."""
        shopembed = discord.Embed(
            title="IdleRPG Store",
            description=f"Welcome! Use `{ctx.prefix}purchase storeitemid` to buy something.",
            colour=discord.Colour.blurple(),
        )
        shopembed.add_field(
            name="Boosters",
            value="`#1` Time Booster\t**$1000**\tBoosts adventure time by 50%\n`#2` Luck Booster\t**$500**\tBoosts adventure luck by 25%\n`#3` Money Booster\t**$1000**\tBoosts adventure money rewards by 25%",
            inline=False,
        )
        shopembed.set_thumbnail(url=f"{self.bot.BASE_URL}/business.png")
        await ctx.send(embed=shopembed)

    @has_char()
    @commands.command()
    async def purchase(self, ctx, item: str.lower, amount: IntGreaterThan(0) = 1):
        """Buy a booster from the store."""
        try:
            price = {"time": 1000, "luck": 500, "money": 1000}[item] * amount
        except KeyError:
            return await ctx.send(f"Please either buy `time`, `luck` or `money` instead of `{item}`.")
        if ctx.character_data["money"] < price:
            return await ctx.send("You're too poor.")
        await conn.execute(
            f'UPDATE profile SET {item}_booster={item}_booster+$1, "money"="money"-$2 WHERE "user"=$3;',
            amount,
            price,
            ctx.author.id,
        )
        await ctx.send(
            f"Successfully bought **{amount}** store item `{item}`. Use `{ctx.prefix}boosters` to view your new boosters."
        )

    @has_char()
    @commands.command()
    async def boosters(self, ctx):
        """View your boosters."""
        timeboosters = ctx.character_data["time_booster"]
        luckboosters = ctx.character_data["luck_booster"]
        moneyboosters = ctx.character_data["money_booster"]
        time = await self.bot.get_booster(ctx.author, "time")
        luck = await self.bot.get_booster(ctx.author, "luck")
        money = await self.bot.get_booster(ctx.author, "money")
        time = f"Time booster - {str(time).split('.')[0]}" if time else None
        luck = f"Luck booster - {str(luck).split('.')[0]}" if luck else None
        money = f"Money booster - {str(money).split('.')[0]}" if money else None
        actives = "\n".join([b for b in [time, luck, money] if b])
        if time or luck or money:
            desc = f"**Currently active**\n{actives}"
        else:
            desc = ""
        await ctx.send(
            embed=discord.Embed(
                title="Your Boosters",
                description=f"{desc}\n\nTime Boosters: `{timeboosters}`\nLuck Boosters: `{luckboosters}`\nMoney Boosters: `{moneyboosters}`",
                colour=discord.Colour.blurple(),
            ).set_footer(text=f"Use {ctx.prefix}activate to activate one")
        )

    @has_char()
    @commands.command()
    async def activate(self, ctx, boostertype: str):
        """Activate a booster."""
        if boostertype not in ["time", "luck", "money"]:
            return await ctx.send(
                "That is not a valid booster type. Must be `time/luck/money`."
            )
        boosters = ctx.character_data[f"{boostertype}_booster"]
        if not boosters:
            return await ctx.send("You don't have any of these boosters.")
        check = await self.bot.get_booster(ctx.author, boostertype)
        if check:
            return await ctx.send("This booster is already running.")
        await self.bot.pool.execute(
            f'UPDATE profile SET "{boostertype}_booster"="{boostertype}_booster"-1 WHERE "user"=$1;',
            ctx.author.id,
        )
        await self.bot.activate_booster(ctx.author, boostertype)
        await ctx.send(
            f"Successfully activated a **{boostertype.title()} booster** for the next **24 hours**!"
        )


def setup(bot):
    bot.add_cog(Store(bot))
