"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import random

import discord
from discord.ext import commands

from classes.converters import IntGreaterThan, MemberWithCharacter
from utils.checks import has_char


class Crates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @commands.command(aliases=["boxes"])
    async def crates(self, ctx):
        """Shows your crates."""
        await ctx.send(
            f"You currently have **{ctx.character_data['crates']}** crates, {ctx.author.mention}! "
            f"Use `{ctx.prefix}open` to open one!"
        )

    @has_char()
    @commands.command(name="open")
    async def _open(self, ctx):
        """Opens a crate."""
        if ctx.character_data["crates"] < 1:
            return await ctx.send(
                "Seems like you don't have a crate yet. Vote me up to get some or earn them!"
            )
        rand = random.randint(1, 6)
        if rand == 1:
            minstat, maxstat = (20, 30)
        elif rand == 2 or rand == 3:
            minstat, maxstat = (10, 19)
        else:
            minstat, maxstat = (1, 9)

        item = await self.bot.create_random_item(minstat=minstat, maxstat=maxstat, minvalue=1, maxvalue=250, owner=ctx.author)

        embed = discord.Embed(
            title="You gained an item!",
            description="You found a new item when opening a crate!",
            color=0xFF0000,
        )
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.add_field(name="ID", value=item["id"], inline=False)
        embed.add_field(name="Name", value=item["name"], inline=False)
        embed.add_field(name="Type", value=item["type"], inline=False)
        embed.add_field(name="Damage", value=item["damage"], inline=True)
        embed.add_field(name="Armor", value=item["armor"], inline=True)
        embed.add_field(name="Value", value=f"${item['value']}", inline=False)
        embed.set_footer(text=f"Remaining crates: {ctx.character_data['crates'] - 1}")
        await ctx.send(embed=embed)

    @has_char()
    @commands.command()
    async def tradecrate(
        self, ctx, other: MemberWithCharacter, amount: IntGreaterThan(0) = 1
    ):
        """Trades crates to a user."""
        if other == ctx.author:
            return await ctx.send("Very funny...")
        if ctx.character_data["crates"] < amount:
            return await ctx.send("You don't have any crates.")
        async with self.bot.pool.acquire() as conn:
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
