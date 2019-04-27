"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import asyncio
import datetime
import random
from decimal import Decimal

import discord
from discord.ext import commands

from cogs.classes import genstats
from utils.checks import has_char, has_money, is_admin


def in_raid():
    def predicate(ctx):
        return ctx.author in ctx.bot.raid and ctx.channel.id == 506_133_354_874_404_874

    return commands.check(predicate)


def can_join():
    def predicate(ctx):
        return ctx.bot.boss_is_spawned and ctx.author not in ctx.bot.raid

    return commands.check(predicate)


def raid_channel():
    def predicate(ctx):
        return ctx.channel.id == 506_133_354_874_404_874

    return commands.check(predicate)


class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.boss_is_spawned = False
        self.bot.raid = {}
        self.allow_sending = discord.PermissionOverwrite(
            send_messages=True, read_messages=True
        )
        self.deny_sending = discord.PermissionOverwrite(
            send_messages=False, read_messages=False
        )
        self.read_only = discord.PermissionOverwrite(
            send_messages=False, read_messages=True
        )

    @is_admin()
    @raid_channel()
    @commands.command()
    async def spawn(self, ctx, hp: int):
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        self.bot.boss_is_spawned = True
        boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            f"""
**ATTENTION! ZEREKIEL HAS SPAWNED!**
This boss has {boss['hp']} HP and has high-end loot!
The dragon will be vulnerable in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!
""",
            file=discord.File("assets/other/dragon.jpg"),
        )
        try:
            await self.bot.get_channel(506_133_354_874_404_874).send(
                "@everyone Zerekiel spawned! 15 Minutes until he is vulnerable...\nUse https://raid.travitia.xyz/ to join the raid!"
            )
        except discord.Forbidden:
            await ctx.channel.set_permissions(
                ctx.guild.default_role, overwrite=self.deny_sending
            )
            self.bot.boss_is_spawned = False
            return await ctx.send(
                "Honestly... I COULD NOT SEND THE SPAWN MESSAGE IN #RAID-MAIN GUYS!!!"
            )
        await asyncio.sleep(300)
        await ctx.send("**The dragon will be vulnerable in 10 minutes**")
        await asyncio.sleep(300)
        await ctx.send("**The dragon will be vulnerable in 5 minutes**")
        await asyncio.sleep(180)
        await ctx.send("**The dragon will be vulnerable in 2 minutes**")
        await asyncio.sleep(60)
        await ctx.send("**The dragon will be vulnerable in 1 minute**")
        await asyncio.sleep(30)
        await ctx.send("**The dragon will be vulnerable in 30 seconds**")
        await asyncio.sleep(20)
        await ctx.send("**The dragon will be vulnerable in 10 seconds**")
        await asyncio.sleep(10)
        await ctx.send(
            "**The dragon is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            self.bot.raid2 = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Sword",
                self.bot.raid2,
            )
            deffs = await conn.fetch(
                'SELECT p."user", ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Shield",
                self.bot.raid2,
            )
        for i in self.bot.raid2:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            dmg = 0
            deff = 0
            for j in dmgs:
                if j["user"] == i:
                    dmg = j["damage"] * j["atkmultiply"]
            for j in deffs:
                if j["user"] == i:
                    deff = j["armor"] * j["defmultiply"]
            dmg, deff = await genstats(self.bot, i, dmg, deff)
            self.bot.raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        if not self.bot.raid:
            return await ctx.send(
                "Noone joined for killing Zerekiel... Sadly the boss will now vanish..."
            )
        else:
            await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(self.bot.raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=30)
        ):
            target = random.choice(list(self.bot.raid.keys()))  # the guy it will attack
            dmg = random.randint(
                boss["min_dmg"], boss["max_dmg"]
            )  # effective damage the dragon does
            dmg -= self.bot.raid[target]["armor"]  # let's substract the shield, ouch
            self.bot.raid[target]["hp"] -= dmg  # damage dealt
            if self.bot.raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} now has {self.bot.raid[target]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} died!",
                    colour=0xFFB900,
                )
            em.add_field(
                name="Theoretical Damage", value=dmg + self.bot.raid[target]["armor"]
            )
            em.add_field(name="Shield", value=self.bot.raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/dragon.png")
            await ctx.send(embed=em)
            if self.bot.raid[target]["hp"] <= 0:
                del self.bot.raid[target]
            dmg_to_take = 0
            for i in self.bot.raid:
                dmg_to_take += self.bot.raid[i]["damage"]
            boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Zerekiel!", colour=0xFF5C00)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/knight.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if boss["hp"] > 0:
                em.add_field(name="HP left", value=boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(embed=em)
            await asyncio.sleep(4)

        self.bot.boss_is_spawned = False

        if len(self.bot.raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif boss["hp"] < 1:
            await ctx.channel.set_permissions(
                ctx.guild.default_role, overwrite=self.allow_sending
            )
            weapon_stat = random.randint(42, 50)
            weapon_type = random.choice(["Sword", "Shield"])
            name_mid = random.choice(["Ferocious", "Bloody", "Glimmering"])
            weapon_name = f"Zerekiel's {name_mid} {weapon_type}"
            highest_bid = [
                ctx.guild.get_member(356_091_260_429_402_122),
                0,
            ]  # user, amount

            def check(msg):
                if (
                    msg.channel.id != ctx.channel.id
                    or (not msg.content.isdigit())
                    or (msg.author not in self.bot.raid)
                ):
                    return False
                if not (int(msg.content) > highest_bid[1]):
                    return False
                return True

            page = commands.Paginator()
            page.add_line(
                f"The raid killed the boss!\nHe dropped {weapon_name}, with a stat of {weapon_stat}!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!\n\nPeople eligible for bids:\n\n"
            )
            for u in list(self.bot.raid.keys()):
                page.add_line(u.mention)
            for p in page.pages:
                await ctx.send(p[4:-4])

            while True:
                try:
                    msg = await self.bot.wait_for("message", timeout=60, check=check)
                except asyncio.TimeoutError:
                    break
                bid = int(msg.content)
                money = await self.bot.pool.fetchval(
                    'SELECT money FROM profile WHERE "user"=$1;', msg.author.id
                )
                if money and bid > highest_bid[1] and money >= bid:
                    highest_bid = [msg.author, bid]
                    await ctx.send(f"{msg.author.mention} bids **${msg.content}**!")
            msg = await ctx.send(
                f"Auction done! Winner is {highest_bid[0].mention} with **${highest_bid[1]}**!\nGiving weapon..."
            )
            money = await self.bot.pool.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', highest_bid[0].id
            )
            if money >= highest_bid[1]:
                if weapon_type == "Sword":
                    id = await self.bot.pool.fetchval(
                        'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING "id";',
                        highest_bid[0].id,
                        weapon_name,
                        1,
                        weapon_type,
                        weapon_stat,
                        0,
                    )
                else:
                    id = await self.bot.pool.fetchval(
                        'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING "id";',
                        highest_bid[0].id,
                        weapon_name,
                        1,
                        weapon_type,
                        0,
                        weapon_stat,
                    )
                await self.bot.pool.execute(
                    'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                    id,
                    False,
                )
                await self.bot.pool.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    highest_bid[1],
                    highest_bid[0].id,
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / len(self.bot.raid))  # what da hood gets per survivor
            async with self.bot.pool.acquire() as conn:
                for u in self.bot.raid:
                    await conn.execute(
                        'UPDATE profile SET money=money+$1 WHERE "user"=$2;', cash, u.id
                    )
            await ctx.send(
                f"**Gave ${cash} of Zerekiel's ${hp} drop to all survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Zerekiel within 30 Minutes... He disappeared!"
            )

        await asyncio.sleep(30)
        self.bot.raid = {}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    def getpriceto(self, level: float):
        return sum(i * 25000 for i in range(1, int(level * 10) - 9))

    @has_char()
    @commands.group(invoke_without_command=True)
    async def increase(self, ctx):
        """Upgrade your raid damage or defense multiplier."""
        await ctx.send(
            f"Use `{ctx.prefix}increase damage/defense` to upgrade your raid damage/defense multiplier by 10%."
        )

    @increase.command()
    async def damage(self, ctx):
        """Increase your raid damage."""
        async with self.bot.pool.acquire() as conn:
            lvl = await conn.fetchval(
                'SELECT atkmultiply FROM profile WHERE "user"=$1;', ctx.author.id
            )
            newlvl = lvl + Decimal("0.1")
            price = self.getpriceto(newlvl)
            if not await has_money(self.bot, ctx.author.id, price):
                return await ctx.send(
                    f"Upgrading your weapon attack raid multiplier to {newlvl} costs **${price}**, you are too poor."
                )
            await conn.execute(
                'UPDATE profile SET "atkmultiply"=$1, "money"="money"-$2 WHERE "user"=$3;',
                newlvl,
                price,
                ctx.author.id,
            )
        await ctx.send(
            f"You upgraded your weapon attack raid multiplier to {newlvl} for **${price}**."
        )

    @increase.command()
    async def defense(self, ctx):
        """Increase your raid defense."""
        async with self.bot.pool.acquire() as conn:
            lvl = await conn.fetchval(
                'SELECT defmultiply FROM profile WHERE "user"=$1;', ctx.author.id
            )
            newlvl = lvl + Decimal("0.1")
            price = self.getpriceto(newlvl)
            if not await has_money(self.bot, ctx.author.id, price):
                return await ctx.send(
                    f"Upgrading your shield defense raid multiplier to {newlvl} costs **${price}**, you are too poor."
                )
            await conn.execute(
                'UPDATE profile SET "defmultiply"=$1, "money"="money"-$2 WHERE "user"=$3;',
                newlvl,
                price,
                ctx.author.id,
            )
        await ctx.send(
            f"You upgraded your shield defense raid multiplier to {newlvl} for **${price}**."
        )

    @has_char()
    @commands.command()
    async def raidstats(self, ctx):
        """View your raid stats."""
        data = await self.bot.pool.fetchrow(
            'SELECT atkmultiply, defmultiply FROM profile WHERE "user"=$1;',
            ctx.author.id,
        )
        atk = data["atkmultiply"]
        deff = data["defmultiply"]
        atkp = self.getpriceto(atk + Decimal("0.1"))
        deffp = self.getpriceto(deff + Decimal("0.1"))
        await ctx.send(
            f"**{ctx.author.mention}'s raid multipliers**\nDamage Multiplier: x{atk} (Upgrading: ${atkp})\nDefense Multiplier: x{deff} (Upgrading: ${deffp})"
        )

    @commands.command()
    async def raid(self, ctx):
        await ctx.send(
            f"Did you ever want to join together with other players to defeat the dragon that roams this land? Raids got you covered!\nJoin the support server (`{ctx.prefix}support`) for more information."
        )


def setup(bot):
    bot.add_cog(Raid(bot))
