"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import random
import secrets
import utils.checks as checks

from discord.ext import commands


class Halloween(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.waiting = None

    def cog_check(self, ctx):
        return ctx.author.id == 287_215_355_137_622_016

    @checks.has_char()
    @commands.cooldown(1, 43200, commands.BucketType.user)
    @commands.command(description="Trick or Treat!")
    async def trickortreat(self, ctx):
        # temp
        waiting = self.bot.waiting
        if not waiting:
            self.bot.waiting = ctx.author
            return await ctx.send(
                "You walk around the houses... Noone is there... *yet*"
            )
        if secrets.randbelow(2) == 1:
            await ctx.send(
                f"You walk around the houses and ring at {waiting}'s house! That's a trick or treat bag for you, yay!"
            )
            await self.bot.pool.execute(
                'UPDATE profile SET trickortreat=trickortreat+1 WHERE "user"=$1;',
                ctx.author.id,
            )
        else:
            await ctx.send(
                f"You walk around the houses and ring at {waiting}'s house! Sadly they don't have anything for you..."
            )
        try:
            if secrets.randbelow(2) == 1:
                await waiting.send(
                    f"The waiting was worth it: {ctx.author} rang! That's a trick or treat bag for you, yay!"
                )
                await self.bot.pool.execute(
                    'UPDATE profile SET trickortreat=trickortreat+1 WHERE "user"=$1;',
                    waiting.id,
                )
            else:
                await waiting.send(
                    f"{ctx.author} rings at your house, but... Nothing for you!"
                )
        except discord.Forbidden:
            pass
        finally:
            self.bot.waiting = None
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money+50 WHERE "user"=$1', ctx.author.id
            )
            usr = await conn.fetchval(
                'SELECT "user" FROM profile WHERE "money">=50 ORDER BY RANDOM() LIMIT 1;'
            )
            await conn.execute(
                'UPDATE profile SET money=money-50 WHERE "user"=$1;', usr
            )
        usr = self.bot.get_user(usr) or "Unknown User"
        await ctx.send(f"{usr} gave you additional $50!")

    @checks.has_char()
    @commands.command(description="Open a trick or treat bag!")
    async def yummy(self, ctx):
        # better name?
        async with self.bot.pool.acquire() as conn:
            bags = await conn.fetchval(
                'SELECT trickortreat FROM profile WHERE "user"=$1;', ctx.author.id
            )
            if bags < 1:
                return await ctx.send(
                    "Seems you haven't got a trick or treat bag yet. Go get some!"
                )
            mytry = random.randint(1, 6)
            if mytry == 1:
                maximumstat = float(random.randint(20, 30))
            elif mytry == 2 or mytry == 3:
                maximumstat = float(random.randint(10, 19))
            else:
                maximumstat = float(random.randint(1, 9))
            shieldorsword = random.choice(["Sword", "Shield"])
            names = [
                "Jack's",
                "Spooky",
                "Ghostly",
                "Skeletal",
                "Glowing",
                "Moonlight",
                "Adrian's really awesome",
            ]
            itemvalue = random.randint(1, 250)
            if shieldorsword == "Sword":
                itemname = f'{random.choice(names)} {random.choice(["Sword", "Blade", "Stich", "Arm", "Bone"])}'
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
                itemname = f'{random.choice(names)} {random.choice(["Shield", "Defender", "Aegis", "Shadow Shield", "Giant Ginger"])}'
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
                'UPDATE profile SET trickortreat=trickortreat-1 WHERE "user"=$1;',
                ctx.author.id,
            )
        embed = discord.Embed(
            title="You gained an item!",
            description="You found a new item when opening a trick-or-treat bag!",
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
        embed.set_footer(text=f"Remaining trick-or-treat bags: {bags-1}")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Halloween(bot))
