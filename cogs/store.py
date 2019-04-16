"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import datetime

from discord.ext import commands
from utils.checks import has_char, has_money


class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="The store. Buy boosters here.")
    async def store(self, ctx):
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
    async def purchase(self, ctx, item: int, amount: int = 1):
        """Buy a booster from the store."""
        if item < 1 or item > 3:
            return await ctx.send("Enter a valid booster to buy.")
        price = [1000, 500, 1000][item - 1] * amount
        if not await has_money(self.bot, ctx.author.id, price):
            return await ctx.send("You're too poor.")
        async with self.bot.pool.acquire() as conn:
            if item == 1:
                await conn.execute(
                    'UPDATE profile SET time_booster=time_booster+$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
            elif item == 2:
                await conn.execute(
                    'UPDATE profile SET luck_booster=luck_booster+$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
            elif item == 3:
                await conn.execute(
                    'UPDATE profile SET money_booster=money_booster+$1 WHERE "user"=$2;',
                    amount,
                    ctx.author.id,
                )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                price,
                ctx.author.id,
            )
        await ctx.send(
            f"Successfully bought **{amount}** store item `{item}`. Use `{ctx.prefix}boosters` to view your new boosters."
        )

    @has_char()
    @commands.command(description="View your boosters.")
    async def boosters(self, ctx):
        async with self.bot.pool.acquire() as conn:
            boosters = await conn.fetchval(
                'SELECT (time_booster, luck_booster, money_booster) FROM profile WHERE "user"=$1;',
                ctx.author.id,
            )
            timeboosters = boosters[0]
            luckboosters = boosters[1]
            moneyboosters = boosters[2]
            active = []
            booster = ["`Time Booster`", "`Luck Booster`", "`Money Booster`"]
            active = await conn.fetch(
                'SELECT "type", "end" FROM boosters WHERE "end" > clock_timestamp() AND "user"=$1;',
                ctx.author.id,
            )
        nl = "\n"
        await ctx.send(
            embed=discord.Embed(
                title="Your Boosters",
                description=f"{'**Currently Active**'+nl if active!=[] else ''}{nl.join([booster[row[0]-1]+' active for another '+str(row[1]-datetime.datetime.now(datetime.timezone.utc)).split('.')[0] for row in active])}\n\nTime Boosters: `{timeboosters}`\nLuck Boosters: `{luckboosters}`\nMoney Boosters: `{moneyboosters}`",
                colour=discord.Colour.blurple(),
            ).set_footer(text=f"Use {ctx.prefix}activate to activate one")
        )

    @has_char()
    @commands.command(description="Uses a booster.")
    async def activate(self, ctx, boostertype: int):
        if boostertype not in range(1, 4):
            return await ctx.send(
                "That is not a valid booster type. Must be from `1` to `3`."
            )
        booster = ["time_booster", "luck_booster", "money_booster"][boostertype - 1]
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchval(
                f'SELECT {booster} FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if res == 0:
                return await ctx.send("You don't have any of these boosters.")
            check = await conn.fetchrow(
                'SELECT * FROM boosters WHERE "type"=$1 AND "user"=$2;',
                boostertype,
                ctx.author.id,
            )
            check2 = await conn.fetchrow(
                'SELECT * FROM boosters WHERE "type"=$1 AND "user"=$2 AND clock_timestamp() > "end";',
                boostertype,
                ctx.author.id,
            )
            if check and not check2:
                return await ctx.send(
                    f"You already have one of these boosters active! Use `{ctx.prefix}boosters` to see how long it still lasts."
                )
            elif check and check2:
                await conn.execute(
                    'DELETE FROM boosters WHERE "type"=$1 AND "user"=$2;',
                    boostertype,
                    ctx.author.id,
                )
            await conn.execute(
                f'UPDATE profile SET {booster}={booster}-1 WHERE "user"=$1;',
                ctx.author.id,
            )
            end = await conn.fetchval("SELECT clock_timestamp() + interval '1d';")
            await conn.execute(
                'INSERT INTO boosters ("user", "type", "end") VALUES ($1, $2, $3);',
                ctx.author.id,
                boostertype,
                end,
            )
        await ctx.send(
            f"Successfully activated a **{booster.replace('_', ' ').capitalize()}** for the next **24 hours**!"
        )


def setup(bot):
    bot.add_cog(Store(bot))
