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
from utils.checks import has_char, is_admin


def raid_channel():
    def predicate(ctx):
        return ctx.channel.id == 506_133_354_874_404_874

    return commands.check(predicate)


def ikhdosa_channel():
    def predicate(ctx):
        return ctx.channel.id == 561_929_996_952_797_217

    return commands.check(predicate)


class Raid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        """[Bot Admin only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
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

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/dragon.jpg"),
        )
        await self.bot.get_channel(506_167_065_464_406_041).send(
            "@everyone Zerekiel spawned! 15 Minutes until he is vulnerable...\nUse https://raid.travitia.xyz/ to join the raid!"
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
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Sword",
                raid_raw,
            )
            deffs = await conn.fetch(
                'SELECT p."user", ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Shield",
                raid_raw,
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await genstats(self.bot, i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))  # the guy it will attack
            dmg = random.randint(
                boss["min_dmg"], boss["max_dmg"]
            )  # effective damage the dragon does
            dmg -= raid[target]["armor"]  # let's substract the shield, ouch
            raid[target]["hp"] -= dmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} died!",
                    colour=0xFFB900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/dragon.png")
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
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

        if len(raid) == 0:
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
                    or (msg.author not in raid)
                ):
                    return False
                if not (int(msg.content) > highest_bid[1]):
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                f"The raid killed the boss!\nHe dropped a weapon/shield of unknown stat in the range of 42 to 50!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!"
            )
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
                if money and money >= bid:
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
                await msg.edit(content=f"{msg.content} Done! The weapon was {weapon_name} with a stat of {weapon_stat}!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp * 2 / len(raid))  # what da hood gets per survivor
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                [u.id for u in raid.keys()],
            )
            await ctx.send(
                f"**Gave ${cash} of Zerekiel's ${hp * 2} drop to all survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Zerekiel within 45 Minutes... He disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    @is_admin()
    @ikhdosa_channel()
    @commands.command()
    async def raiddefend(self, ctx, bandits: int, group: str = "I"):
        """[Bot Admin only] Starts a bandit raid in Ikhdosa."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        bandits = [{"hp": random.randint(70, 120), "id": i + 1} for i in range(bandits)]
        payout = sum(i["hp"] for i in bandits)
        await ctx.send(
            f"""
**Lieutenant**: We've spotted a group of Bandits! Come to the front and help me defend the city gates!
They arrive in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/bandits1.jpg"),
        )
        await asyncio.sleep(300)
        await ctx.send("**The bandits arrive in 10 minutes**")
        await asyncio.sleep(300)
        await ctx.send("**The bandits arrive in 5 minutes**")
        await asyncio.sleep(180)
        await ctx.send("**The bandits arrive in 2 minutes**")
        await asyncio.sleep(60)
        await ctx.send("**The bandits arrive in 1 minute**")
        await asyncio.sleep(30)
        await ctx.send("**The bandits arrive in 30 seconds**")
        await asyncio.sleep(20)
        await ctx.send("**The bandits arrive in 10 seconds**")
        await asyncio.sleep(10)
        await ctx.send("**The bandits arrived! Fetching participant data... Hang on!**")

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Sword",
                raid_raw,
            )
            deffs = await conn.fetch(
                'SELECT p."user", ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Shield",
                raid_raw,
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await genstats(self.bot, i, dmg, deff)
            raid[u] = {"hp": 100, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        target, target_data = random.choice(list(raid.items()))
        while len(
            bandits
        ) > 0 and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45):
            dmg = random.randint(20, 60)  # effective damage the bandit does
            dmg -= target_data["armor"] * Decimal(
                random.choice(["0.2", "0.3"])
            )  # let's substract the shield, ouch
            target_data["hp"] -= dmg  # damage dealt
            em = discord.Embed(title=f"Bandits left: `{len(bandits)}`", colour=0x000000)
            em.set_author(
                name=f"Bandit Raider Group {group}",
                icon_url=f"{self.bot.BASE_URL}/bandits1.jpg",
            )
            em.add_field(name="Bandit HP", value=f"{bandits[0]['hp']} HP left")
            if target_data["hp"] > 0:
                em.add_field(
                    name="Attack", value=f"Bandit is fighting against `{target}`"
                )
            else:
                em.add_field(name="Attack", value=f"Bandit killed `{target}`")
            em.add_field(
                name="Bandit Damage",
                value=f"Has dealt `{dmg}` damage to the swordsman `{target}`",
            )
            em.set_image(url=f"{self.bot.BASE_URL}/bandits2.jpg")
            await ctx.send(embed=em)
            if target_data["hp"] <= 0:
                del raid[target]
                if len(raid) == 0:  # no more raiders
                    break
                target, target_data = random.choice(list(raid.items()))
            bandits[0]["hp"] -= target_data["damage"]
            await asyncio.sleep(7)
            em = discord.Embed(title=f"Swordsmen left: `{len(raid)}`", colour=0x009900)
            em.set_author(
                name=f"Swordsman ({target})",
                icon_url=f"{self.bot.BASE_URL}/swordsman1.jpg",
            )
            em.add_field(
                name="Swordsman HP", value=f"`{target}` got {target_data['hp']} HP left"
            )
            if bandits[0]["hp"] > 0:
                em.add_field(
                    name="Swordsman attack",
                    value=f"Is attacking the bandit and dealt `{target_data['damage']}` damage",
                )
            else:
                money = random.randint(1500, 2300)
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    target.id,
                )
                bandits.pop(0)
                em.add_field(
                    name="Swordsman attack",
                    value=f"Killed the bandit and received ${money}",
                )
            em.set_image(url=f"{self.bot.BASE_URL}/swordsman2.jpg")
            await ctx.send(embed=em)
            await asyncio.sleep(7)

        if len(bandits) == 0:
            await ctx.send(
                "The bandits got defeated, all Swordsmen that are alive are getting their money now..."
            )
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=ANY($2);',
                payout,
                [u.id for u in raid.keys()],
            )
        elif len(raid) == 0:
            await ctx.send("The bandits plundered the town! All swordsmen died!")

    def getpriceto(self, level: float):
        return sum(i * 25000 for i in range(1, int(level * 10) - 9))

    @commands.group(invoke_without_command=True)
    async def increase(self, ctx):
        """Upgrade your raid damage or defense multiplier."""
        await ctx.send(
            f"Use `{ctx.prefix}increase damage/defense` to upgrade your raid damage/defense multiplier by 10%."
        )

    @has_char()
    @increase.command()
    async def damage(self, ctx):
        """Increase your raid damage."""
        newlvl = ctx.character_data["atkmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                f"Upgrading your weapon attack raid multiplier to {newlvl} costs **${price}**, you are too poor."
            )
        await self.bot.pool.execute(
            'UPDATE profile SET "atkmultiply"=$1, "money"="money"-$2 WHERE "user"=$3;',
            newlvl,
            price,
            ctx.author.id,
        )
        await ctx.send(
            f"You upgraded your weapon attack raid multiplier to {newlvl} for **${price}**."
        )

    @has_char()
    @increase.command()
    async def defense(self, ctx):
        """Increase your raid defense."""
        newlvl = ctx.character_data["defmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                f"Upgrading your shield defense raid multiplier to {newlvl} costs **${price}**, you are too poor."
            )
        await self.bot.pool.execute(
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
        atk = ctx.character_data["atkmultiply"]
        deff = ctx.character_data["defmultiply"]
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
