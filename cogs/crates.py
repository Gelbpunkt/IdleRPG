"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import random

import discord
from discord.ext import commands

from utils.checks import has_char


class Crates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(aliases=["boxes"], description="Shows your current crates.")
    async def crates(self, ctx):
        async with self.bot.pool.acquire() as conn:
            crates = await conn.fetchval(
                'SELECT crates FROM profile WHERE "user"=$1;', ctx.author.id
            )
        await ctx.send(
            f"You currently have **{crates}** crates, {ctx.author.mention}! "
            f"Use `{ctx.prefix}open` to open one!"
        )

    @has_char()
    @commands.command(description="Open a crate!", name="open")
    async def _open(self, ctx):
        async with self.bot.pool.acquire() as conn:
            crates = await conn.fetchval(
                'SELECT crates FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if crates < 1:
                return await ctx.send(
                    "Seems like you don't have a crate yet. Vote me up to get some or earn them!"
                )
            mytry = random.randint(1, 6)
            if mytry == 1:
                maximumstat = float(random.randint(20, 30))
            elif mytry == 2 or mytry == 3:
                maximumstat = float(random.randint(10, 19))
            else:
                maximumstat = float(random.randint(1, 9))
            shieldorsword = random.choice(["Sword", "Shield"])
            names = ["Rare", "Ancient", "Normal", "Legendary", "Famous"]
            itemvalue = random.randint(1, 250)
            if shieldorsword == "Sword":
                itemname = random.choice(names) + random.choice(
                    [" Sword", " Blade", " Stich"]
                )
                item = await conn.fetchrow(
                    'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                    ctx.author.id,
                    itemname,
                    itemvalue,
                    "Sword",
                    maximumstat,
                    0.00,
                )
            elif shieldorsword == "Shield":
                itemname = random.choice(names) + random.choice(
                    [" Shield", " Defender", " Aegis"]
                )
                item = await conn.fetchrow(
                    'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                    ctx.author.id,
                    itemname,
                    itemvalue,
                    "Shield",
                    0.00,
                    maximumstat,
                )

            await conn.execute(
                'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                item[0],
                False,
            )
            await conn.execute(
                'UPDATE profile SET crates=crates-1 WHERE "user"=$1;', ctx.author.id
            )

        embed = discord.Embed(
            title="You gained an item!",
            description="You found a new item when opening a crate!",
            color=0xFF0000,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name="ID", value=item[0], inline=False)
        embed.add_field(name="Name", value=itemname, inline=False)
        embed.add_field(name="Type", value=shieldorsword, inline=False)
        if shieldorsword == "Shield":
            embed.add_field(name="Damage", value="0.00", inline=True)
            embed.add_field(name="Armor", value=f"{maximumstat}0", inline=True)
        else:
            embed.add_field(name="Damage", value=f"{maximumstat}0", inline=True)
            embed.add_field(name="Armor", value="0.00", inline=True)
        embed.add_field(name="Value", value=f"${itemvalue}", inline=False)
        embed.set_footer(text=f"Remaining crates: {crates-1}")
        await ctx.send(embed=embed)

    @has_char()
    @commands.command(description="Trades a crate to a user.")
    async def tradecrate(self, ctx, other: discord.Member, amount: int = 1):
        if other == ctx.author or amount < 0:
            return await ctx.send("Very funny...")
        async with self.bot.pool.acquire() as conn:
            crates = await conn.fetchval(
                'SELECT crates FROM profile WHERE "crates">=$1 AND "user"=$2;',
                amount,
                ctx.author.id,
            )
            if not crates:
                return await ctx.send("You don't have any crates.")
            await conn.execute(
                'UPDATE profile SET crates=crates-$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET crates=crates+$1 WHERE "user"=$2;', amount, other.id
            )
        await ctx.send(f"Successfully gave {amount} crate(s) to {other.mention}.")


def setup(bot):
    bot.add_cog(Crates(bot))
