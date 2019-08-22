"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio
import datetime
import random
from decimal import Decimal

import discord
from discord.ext import commands

from classes.converters import IntGreaterThan
from utils.castle import Castle, Player
from utils.checks import has_char, is_admin, is_god


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
    @locale_doc
    async def spawn(self, ctx, hp: IntGreaterThan(0)):
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
        if not self.bot.config.is_beta:
            await self.bot.get_channel(506_167_065_464_406_041).send(
                "@everyone Zerekiel spawned! 15 Minutes until he is vulnerable...\nUse https://raid.travitia.xyz/ to join the raid!"
            )
        if not self.bot.config.is_beta:
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
        else:
            await asyncio.sleep(60)
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
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Sword",
                raid_raw,
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1;',
                "Shield",
                raid_raw,
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            if self.bot.in_class_line(j["class"], "Raider"):
                atkmultiply = j["atkmultiply"] + Decimal(
                    "0.1"
                ) * self.bot.get_class_grade_from(j["class"], "Raider")
            else:
                atkmultiply = j["atkmultiply"]
            dmg = j["damage"] * atkmultiply if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            if self.bot.in_class_line(j["class"], "Raider"):
                defmultiply = j["defmultiply"] + Decimal(
                    "0.1"
                ) * self.bot.get_class_grade_from(j["class"], "Raider")
            else:
                defmultiply = j["defmultiply"]
            deff = j["armor"] * defmultiply if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
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
                if (
                    msg.author.id == highest_bid[0].id
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!"
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
                f"Auction done! Winner is {highest_bid[0].mention} with **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.pool.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', highest_bid[0].id
            )
            if money >= highest_bid[1]:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"-$1, "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                    highest_bid[1],
                    highest_bid[0].id,
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                [u.id for u in raid.keys()],
            )
            await ctx.send(
                f"**Gave ${cash} of Zerekiel's ${int(hp / 4)} drop to all survivors!**"
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
    @locale_doc
    async def raiddefend(self, ctx, bandits: IntGreaterThan(1), group: str = "I"):
        """[Bot Admin only] Starts a bandit raid in Ikhdosa."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        bandits = [
            {"hp": random.randint(100, 120), "id": i + 1} for i in range(bandits)
        ]
        payout = sum(i["hp"] for i in bandits)
        await ctx.send(
            """
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
            if j is None:
                continue
            if self.bot.in_class_line(j["class"], "Raider"):
                atkmultiply = j["atkmultiply"] + Decimal(
                    "0.1"
                ) * self.bot.get_class_grade_from(j["class"], "Raider")
            else:
                atkmultiply = j["atkmultiply"]
            dmg = j["damage"] * atkmultiply if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            if self.bot.in_class_line(j["class"], "Raider"):
                defmultiply = j["defmultiply"] + Decimal(
                    "0.1"
                ) * self.bot.get_class_grade_from(j["class"], "Raider")
            else:
                defmultiply = j["defmultiply"]
            deff = j["armor"] * defmultiply if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 100, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        target, target_data = random.choice(list(raid.items()))
        while len(
            bandits
        ) > 0 and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45):
            dmg = random.randint(50, 90)  # effective damage the bandit does
            dmg -= target_data["armor"] * Decimal(
                random.choice(["0.1", "0.2"])
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
                money = random.randint(2000, 3400)
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

    @is_god()
    @commands.command()
    @locale_doc
    async def guiltspawn(self, ctx):
        """[Guilt only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
The goddess Guilt has grown weak from the easy, summer days of the mortals below.  "There must be balance. Show me your guilts, obsessions, and hates. All that taint your soul, show them to me!  Show me your devotion!" she cries, raising a hand and summoning twisted, shadowy wraiths. Some of the mortals flee in terror, some break down in despair, and some reach for a knife and aim inwards.  Yet, many still stand against the shadows, their willpower strong... for now.

Use https://raid.travitia.xyz/ to join the raid!
**You must be a follower of Guilt.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/guilt.jpg"),
        )
        if not self.bot.config.is_beta:
            await self.bot.get_channel(506_167_065_464_406_041).send(
                "@everyone Guilt spawned! 15 Minutes until the terror begins...\nUse https://raid.travitia.xyz/ to join the raid!"
            )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**The terror will begin in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**The terror will begin in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**The terror will begin in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**The terror will begin in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**The terror will begin in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**The terror will begin in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send("**The terror begins! Fetching participant data... Hang on!**")

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Guilt",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Guilt",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while len(raid) > 1 and datetime.datetime.utcnow() < start + datetime.timedelta(
            minutes=45
        ):
            stuff = random.sample(list(raid.items()), 2)  # attacker, target
            attacker = stuff[0]
            target = stuff[1]
            dmg = random.randint(
                round(attacker[1]["damage"] * Decimal("0.5")),
                round(attacker[1]["damage"] * Decimal("1.5")),
            )
            dmg -= target[1]["armor"]
            dmg = 0 if dmg < 0 else dmg
            raid[target[0]]["hp"] -= dmg  # damage dealt
            if raid[target[0]]["hp"] > 0:
                em = discord.Embed(
                    title=f"{attacker[0]} attacked {target[0]}!",
                    description=f"{target[0]} now has {raid[target[0]]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title=f"{attacker[0]} attacked {target[0]}!",
                    description=f"{target[0]} died!",
                    colour=0xFFB900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + target[1]["armor"])
            em.add_field(name="Shield", value=target[1]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target[0]), icon_url=target[0].avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/guilt.jpg")
            await ctx.send(embed=em)
            if raid[target[0]]["hp"] <= 0:
                del raid[target[0]]
            await asyncio.sleep(4)

        if len(raid) == 1:
            survivor = list(raid.keys())[0]
            await ctx.send(
                f"The massacre is over. {survivor.mention} survived as the strongest of all.\nGuilt gave a <:CrateLegendary:598094865678598144> Legendary Crate to them."
            )
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_legendary"="crates_legendary"+1 WHERE "user"=$1;',
                survivor.id,
            )
        else:
            await ctx.send(
                "The raid did not manage to finish within 45 Minutes... Guilt disappeared!"
            )

    @is_god()
    @commands.command()
    @locale_doc
    async def athenaspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Athena only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
Scylla, the 8 headed Hydra lurks around the side of a narrow channel of water, right beside Olympus; She has been there for decades, eating millions of our soldiers. It's your job to take care of her once and for all! I see your strength may be enough to take her down. Worry not you have many other worshippers right by your side. Loot may be waiting for you my men and woman! If you do defeat her. Loot of unimaginable power!

Scylla will be vulnerable in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!

**Only followers of Athena may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/scylla.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**Scylla will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**Scylla will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**Scylla will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**Scylla will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**Scylla will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**Scylla will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**Scylla is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Athena, Goddess of Wisdom",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Athena, Goddess of Wisdom",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
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
            )  # effective damage scylla does
            dmg -= raid[target]["armor"]  # let's substract the shield, ouch
            raid[target]["hp"] -= dmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Scylla attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title="Scylla attacked!",
                    description=f"{target} died!",
                    colour=0xFFB900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/scylla.jpg")
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Scylla!", colour=0xFF5C00)
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
            msg = await ctx.send(
                "Scylla was defeated and left a chest. Be the first to react with 📫 to win it."
            )

            def check(r, u):
                return (
                    r.message.id == msg.id
                    and u in raid
                    and str(r.emoji) == "\U0001f4eb"
                )

            await msg.add_reaction("\U0001f4eb")
            try:
                r, u = await self.bot.wait_for("reaction_add", timeout=60, check=check)
            except asyncio.TimeoutError:
                return

            await ctx.send(f"{u.mention} was first!")

            inside = random.choice(
                [("money", random.randint(50000, 100000))] * 30
                + [("item",)] * 20
                + [("boosters",)] * 15
                + [("crate", random.choice(["magic", "legendary"]))] * 25
                + [("loot", random.randint(100, 10000))] * 10
            )
            cont = inside[0]
            if cont == "money":
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    inside[1],
                    u.id,
                )
                await ctx.send(f"The chest contained **${inside[1]}**.")
            elif cont == "item":
                item = await self.bot.create_random_item(
                    minstat=1, maxstat=41, minvalue=1000, maxvalue=5000, owner=u.id
                )
                await ctx.send(f"The chest contained an item: **{item['name']}**.")
            elif cont == "boosters":
                await self.bot.pool.execute(
                    'UPDATE profile SET "time_booster"="time_booster"+$1, "luck_booster"="luck_booster"+$1, "money_booster"="money_booster"+$1 WHERE "user"=$2;',
                    1,
                    u.id,
                )
                await ctx.send("The chest contained 3 boosters.")
            elif cont == "crate":
                await self.bot.pool.execute(
                    f'UPDATE profile SET "crates_{inside[1]}"="crates_{inside[1]}"+$1 WHERE "user"=$2;',
                    1,
                    u.id,
                )
                await ctx.send(
                    f"The chest contained a {getattr(self.bot.cogs['Crates'].emotes, inside[1])}."
                )
            elif cont == "loot":
                name = random.choice(["Scylla's Head", "Scylla's Arm", "Scylla's Leg"])
                await self.bot.pool.execute(
                    'INSERT INTO loot ("name", "value", "user") VALUES ($1, $2, $3);',
                    name,
                    inside[1],
                    u.id,
                )
                await ctx.send(f"The chest contained **{name}**.")
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=ANY($2);',
                10000,
                [u.id for u in raid],
            )
            await ctx.send("All survivors were given **$10,000**.")
        else:
            await ctx.send(
                "The raid did not manage to kill Scylla within 45 Minutes... It disappeared!"
            )

    @is_god()
    @commands.command()
    @locale_doc
    async def kvothespawn(self, ctx, scrael: IntGreaterThan(1)):
        """[Kvothe only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        scrael = [{"hp": random.randint(80, 100), "id": i + 1} for i in range(scrael)]
        await ctx.send(
            """
The cthae has gathered an army of scrael. Fight for your life!

Use https://raid.travitia.xyz/ to join the raid!
**Only Kvothe's followers may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/cthae.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**The scrael arrive in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**The scrael arrive in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**The scrael arrive in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**The scrael arrive in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**The scrael arrive in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**The scrael arrive in 10 seconds**")
            await asyncio.sleep(10)
            await ctx.send(
                "**The scrael arrived! Fetching participant data... Hang on!**"
            )
        else:
            await asyncio.sleep(60)
        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Kvothe",
            )
            deffs = await conn.fetch(
                'SELECT p."user", ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Kvothe",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 100, "armor": deff, "damage": dmg, "kills": 0}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            len(scrael) > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target, target_data = random.choice(list(raid.items()))
            dmg = random.randint(50, 90)
            dmg -= target_data["armor"] * Decimal(random.choice(["0.4", "0.5"]))
            target_data["hp"] -= dmg
            em = discord.Embed(title=f"Scrael left: `{len(scrael)}`", colour=0x000000)
            em.add_field(name="Scrael HP", value=f"{scrael[0]['hp']} HP left")
            if target_data["hp"] > 0:
                em.add_field(
                    name="Attack", value=f"Scrael is fighting against `{target}`"
                )
            else:
                em.add_field(name="Attack", value=f"Scrael killed `{target}`")
            em.add_field(
                name="Scrael Damage", value=f"Has dealt `{dmg}` damage to `{target}`"
            )
            em.set_image(url=f"{self.bot.BASE_URL}/scrael.jpg")
            await ctx.send(embed=em)
            if target_data["hp"] <= 0:
                del raid[target]
                if len(raid) == 0:  # no more raiders
                    break
            scrael[0]["hp"] -= target_data["damage"]
            await asyncio.sleep(7)
            em = discord.Embed(title=f"Heroes left: `{len(raid)}`", colour=0x009900)
            em.set_author(
                name=f"Hero ({target})", icon_url=f"{self.bot.BASE_URL}/swordsman1.jpg"
            )
            em.add_field(
                name="Hero HP", value=f"`{target}` got {target_data['hp']} HP left"
            )
            if scrael[0]["hp"] > 0:
                em.add_field(
                    name="Hero attack",
                    value=f"Is attacking the scrael and dealt `{target_data['damage']}` damage",
                )
            else:
                money = random.randint(1500, 2600)
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    target.id,
                )
                scrael.pop(0)
                em.add_field(
                    name="Hero attack", value=f"Killed the scrael and received ${money}"
                )
                raid[target]["kills"] += 1
            em.set_image(url=f"{self.bot.BASE_URL}/swordsman2.jpg")
            await ctx.send(embed=em)
            await asyncio.sleep(7)

        if len(scrael) == 0:
            most_kills = sorted(raid.items(), key=lambda x: -(x[1]["kills"]))[0][0]
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_legendary"="crates_legendary"+$1 WHERE "user"=$2;',
                1,
                most_kills.id,
            )
            await ctx.send(
                f"The scrael were defeated! Our most glorious hero, {most_kills.mention}, has received Kvothe's grace, a {self.bot.cogs['Crates'].emotes.legendary}."
            )
        elif len(raid) == 0:
            await ctx.send(
                "The scrael have extinguished life in Kvothe's temple! All heroes died!"
            )

    @is_god()
    @commands.command()
    @locale_doc
    async def chamburrspawn(self, ctx, hp: IntGreaterThan(0)):
        """[CHamburr only] Starts a raid."""
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
*Time to eat the hamburger! No, this time, the hamburger will eat you up...*

This boss has {boss['hp']} HP and has high-end loot!
The hamburger will be vulnerable in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!
**Only followers of CHamburr may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/hamburger.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**The hamburger will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**The hamburger will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**The hamburger will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**The hamburger will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**The hamburger will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**The hamburger will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**The hamburger is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "CHamburr",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "CHamburr",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))  # the guy it will attack
            dmg = random.randint(boss["min_dmg"], boss["max_dmg"])
            dmg -= raid[target]["armor"]
            raid[target]["hp"] -= dmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Hamburger attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title="Hamburger attacked!",
                    description=f"{target} died!",
                    colour=0xFFB900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/hamburger.jpg")
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(
                title="The raid attacked the hamburger!", colour=0xFF5C00
            )
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
                if (
                    msg.author.id == highest_bid[0].id
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!"
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
                f"Auction done! Winner is {highest_bid[0].mention} with **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.pool.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', highest_bid[0].id
            )
            if money >= highest_bid[1]:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"-$1, "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                    highest_bid[1],
                    highest_bid[0].id,
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                [u.id for u in raid.keys()],
            )
            await ctx.send(
                f"**Gave ${cash} of the hamburger's ${int(hp / 4)} drop to all survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill the hamburger within 45 Minutes... He disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    @is_god()
    @commands.command()
    @locale_doc
    async def salutationsspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Salutations only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
**ALERT! CYBERUS has been summoned and is ENRAGED! CYBERUS: "Those who dare defile and seek wealth and power from me shall be purished..."**

The bestie will be vulnerable in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!

**Only followers of Salutations may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/cyberus.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**Cyberus will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**Cyberus will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**Cyberus will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**Cyberus will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**Cyberus will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**Cyberus will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**Cyberus is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Salutations",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Salutations",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))
            msg = await ctx.send(f"Letting {target.mention} choose an action...")
            try:
                action = ["Greater Heal", "Second Wind", "Block"][
                    await self.bot.paginator.Choose(
                        entries=[
                            "Greater Heal: Heal yourself for 40% HP",
                            "Second Wind: Increase all users' damage by 50%",
                            "Block: Block the attack with 50% chance",
                        ],
                        title="Choose a Raid Action",
                        timeout=10,
                        return_index=True,
                    ).paginate(ctx, location=target)
                ]
            except self.bot.paginator.NoChoice:
                action = None
            cyberus_skill = random.choice(["enragement", "assassinate", "howl"])
            if action == "Greater Heal":
                raid[target]["hp"] += 63
                if raid[target]["hp"] > 250:
                    raid[target]["hp"] = 250
            if action == "Block" and random.randint(1, 10) < 5:
                await ctx.send(f"{target.mention} blocked the attack by Cyberus.")
            else:
                if cyberus_skill == "enragement":
                    dmg = round(
                        random.randint(boss["min_dmg"], boss["max_dmg"]) * 1.4
                    )  # 40% more
                    dmg -= raid[target]["armor"]
                    raid[target]["hp"] -= dmg  # damage dealt
                    if raid[target]["hp"] > 0:
                        em = discord.Embed(
                            title="Cyberus attacked!",
                            description=f"{target} now has {raid[target]['hp']} HP!",
                            colour=0xFFB900,
                        )
                    else:
                        em = discord.Embed(
                            title="Cyberus attacked!",
                            description=f"{target} died!",
                            colour=0xFFB900,
                        )
                    em.add_field(
                        name="Theoretical Damage", value=dmg + raid[target]["armor"]
                    )
                    em.add_field(name="Shield", value=raid[target]["armor"])
                    em.add_field(name="Effective Damage", value=dmg)
                    em.set_author(name=str(target), icon_url=target.avatar_url)
                    em.set_thumbnail(url=f"{self.bot.BASE_URL}/cyberus.jpg")
                    await ctx.send(
                        "Cyberus used **enragement**: Attack is increased by 40% but is more susceptible to damage by 10%.",
                        embed=em,
                    )
                    if raid[target]["hp"] <= 0:
                        del raid[target]
                elif cyberus_skill == "assassinate" and random.randint(1, 10) < 5:
                    del raid[target]
                    await ctx.send(
                        "Cyberus successfully used **assassinate** and kills a player regardless of HP.",
                        embed=discord.Embed(
                            title="Cyberus assassinated!",
                            description=f"{target} died.",
                            colour=0xFFB900,
                        )
                        .set_author(name=str(target), icon_url=target.avatar_url)
                        .set_thumbnail(url=f"{self.bot.BASE_URL}/cyberus.jpg"),
                    )
                else:
                    if cyberus_skill == "assassinate":
                        text = "Cyberus failed to use **assassinate**."
                    else:
                        text = "Cyberus used **howl** to lower player damage by 30%."
                    dmg = random.randint(boss["min_dmg"], boss["max_dmg"])
                    dmg -= raid[target]["armor"]
                    raid[target]["hp"] -= dmg  # damage dealt
                    if raid[target]["hp"] > 0:
                        em = discord.Embed(
                            title="Cyberus attacked!",
                            description=f"{target} now has {raid[target]['hp']} HP!",
                            colour=0xFFB900,
                        )
                    else:
                        em = discord.Embed(
                            title="Cyberus attacked!",
                            description=f"{target} died!",
                            colour=0xFFB900,
                        )
                    em.add_field(
                        name="Theoretical Damage", value=dmg + raid[target]["armor"]
                    )
                    em.add_field(name="Shield", value=raid[target]["armor"])
                    em.add_field(name="Effective Damage", value=dmg)
                    em.set_author(name=str(target), icon_url=target.avatar_url)
                    em.set_thumbnail(url=f"{self.bot.BASE_URL}/cyberus.jpg")
                    await ctx.send(text, embed=em)
                    if raid[target]["hp"] <= 0:
                        del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            base_dmg = dmg_to_take
            text = ""
            if cyberus_skill == "enragement":
                text = "Cyberus takes **10%** more damage due to **enragement**.\n"
                dmg_to_take += round(base_dmg * 0.1)
            if action == "Second Wind":
                text = f"{text}The players deal **50%** more damage due to **second wind**.\n"
                dmg_to_take += round(base_dmg * 0.5)
            if cyberus_skill == "howl":
                text = f"{text}Cyberus uses **howl** to reduce damage by 30%"
                dmg_to_take -= round(dmg_to_take * Decimal("0.3"))
            boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Cyberus!", colour=0xFF5C00)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/knight.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if boss["hp"] > 0:
                em.add_field(name="HP left", value=boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(text, embed=em)
            await asyncio.sleep(4)

        if len(raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif boss["hp"] < 1:
            await ctx.channel.set_permissions(
                ctx.guild.default_role, overwrite=self.allow_sending
            )
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
                if (
                    msg.author.id == highest_bid[0].id
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!"
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
                f"Auction done! Winner is {highest_bid[0].mention} with **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.pool.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', highest_bid[0].id
            )
            if money >= highest_bid[1]:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"-$1, "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                    highest_bid[1],
                    highest_bid[0].id,
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                [u.id for u in raid.keys()],
            )
            await ctx.send(
                f"**Gave ${cash} of Cyberus' ${int(hp / 4)} drop to all survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Cyberus within 45 Minutes... He disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    @is_god()
    @commands.command()
    @locale_doc
    async def asmodeusspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Asmodeus only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
Asmodeus sends a wave of bloodlust throughout his followers and prepares himself for battle. Prepare yourselves as well, this will not be an easy fight. Join the raid now to battle him and reap the rewards.

Use https://raid.travitia.xyz/ to join the raid!
**Only followers of Asmodeus may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/asmodeus.png"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**Asmodeus will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**Asmodeus will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**Asmodeus will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**Asmodeus will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**Asmodeus will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**Asmodeus will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**The god is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Asmodeus",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Asmodeus",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))
            dmg = random.randint(boss["min_dmg"], boss["max_dmg"])
            dmg -= raid[target]["armor"]
            raid[target]["hp"] -= dmg
            raid_dmg = sum(i["damage"] for i in raid.values())
            boss["hp"] -= raid_dmg
            em = discord.Embed(title="Asmodeus Raid", colour=0xFFB900)
            if (hp := raid[target]["hp"]) > 0:
                em.add_field(name="Attack Target", value=f"{target} ({hp} HP)")
            else:
                em.add_field(name="Attack Target", value=f"{target} (Now dead!)")
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/asmodeus.png")
            em.add_field(name="Raid Damage", value=raid_dmg)
            em.add_field(
                name="Asmodeus HP",
                value=boss_hp if (boss_hp := boss["hp"]) > 0 else "Dead!",
            )
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]

            await asyncio.sleep(4)

        if len(raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif boss["hp"] < 1:
            winner = random.choice(raid)
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_legendary"="crates_legendary"+1 WHERE "user"=$1;',
                winner.id,
            )
            await ctx.send(
                "Asmodeus has been defeated. He will lay low for now. He also left a {self.bot.cogs['Crates'].emotes.legendary} to a random survivor ({winner.mention}) for their bravery. They may not get a second chance next time."
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Asmodeus within 45 Minutes... He disappeared!"
            )

    @is_god()
    @commands.command()
    @locale_doc
    async def anankespawn(self, ctx, hp: IntGreaterThan(0)):
        """[Ananke only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        boss = {"hp": hp, "min_dmg": 10, "max_dmg": 50}
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
A convinced Windows® user tries to attack Idle's server with just his conviction to Windows® to force it to turn off! Convince him to use Linux Distributions (e.g. Fedora) before idle dies for ten minutes!

Use https://raid.travitia.xyz/ to join the raid!
**Only followers of Ananke may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>

> IdleRPG is not affiliated with Windows®, Microsoft© or any other non open-source software or vendor in any way
""",
            file=discord.File("assets/other/windows.png"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 10 minutes**"
            )
            await asyncio.sleep(300)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 5 minutes**"
            )
            await asyncio.sleep(180)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 2 minutes**"
            )
            await asyncio.sleep(60)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 1 minute**"
            )
            await asyncio.sleep(30)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 30 seconds**"
            )
            await asyncio.sleep(20)
            await ctx.send(
                "**The convinced Windows® user will be vulnerable in 10 seconds**"
            )
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**The convinced Windows® user is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Ananke",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Ananke",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while boss[
            "hp"
        ] > 0 and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45):
            target = random.choice(list(raid.keys()))
            dmg = random.randint(boss["min_dmg"], boss["max_dmg"])
            dmg -= raid[target]["armor"]
            raid[target]["damage"] -= dmg
            raid[target]["armor"] -= dmg
            if raid[target]["damage"] < 0:
                raid[target]["damage"] = 0
            if raid[target]["armor"] < 0:
                raid[target]["armor"] = 0
            raid_dmg = sum(i["damage"] for i in raid.values())
            boss["hp"] -= raid_dmg
            em = discord.Embed(title="Convincing a Windows® user", colour=0xFFB900)
            em.add_field(
                name="Attack Target",
                value=f"{target} ({raid[target]['damage']} convinction power; {raid[target]['armor']} personal convinction)",
            )
            em.add_field(
                name="Theoretical Convinction", value=dmg + raid[target]["armor"]
            )
            em.add_field(name="Effective Convinction", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/windows.png")
            em.add_field(name="Raid Convinction", value=raid_dmg)
            em.add_field(
                name="Windows® User Convinction Of Windows®",
                value=boss_hp if (boss_hp := boss["hp"]) > 0 else "Convinced!",
            )
            await ctx.send(embed=em)

            await asyncio.sleep(4)

        if boss["hp"] < 1:
            winner = random.choice(raid)
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_legendary"="crates_legendary"+1 WHERE "user"=$1;',
                winner.id,
            )
            await ctx.send(
                "The Windows® user has been convinced, he is happily using a Linux distribution now. He also left a {self.bot.cogs['Crates'].emotes.legendary} to a random survivor ({winner.mention}) as a thank you. Soon, the squad can convince more people from this planet!"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill the convinced Windows® User within 45 Minutes... He disappeared and continues terrifying the web with Microsoft Edge® and Windows Explorer®!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    @is_god()
    @commands.command()
    @locale_doc
    async def jesusspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Jesus only] Starts a raid."""
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
**Atheistus the Tormentor has returned to earth to punish humanity for their belief.**

This boss has {boss['hp']} HP and has high-end loot!
Atheistus will be vulnerable in 15 Minutes

Use https://raid.travitia.xyz/ to join the raid!
**Only followers of Jesus may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/atheistus.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**Atheistus will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**Atheistus will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**Atheistus will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**Atheistus will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**Atheistus will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**Atheistus will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**Atheistus is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Jesus",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Jesus",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] * j["atkmultiply"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] * j["defmultiply"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))
            dmg = random.randint(boss["min_dmg"], boss["max_dmg"])
            dmg -= raid[target]["armor"]
            raid[target]["hp"] -= dmg
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Atheistus attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xFFB900,
                )
            else:
                em = discord.Embed(
                    title="Atheistus attacked!",
                    description=f"{target} died!",
                    colour=0xFFB900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/atheistus.jpg")
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Atheistus!", colour=0xFF5C00)
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
                if (
                    msg.author.id == highest_bid[0].id
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest bid for it wins <:roosip:505447694408482846>\nSimply type how much you bid!"
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
                f"Auction done! Winner is {highest_bid[0].mention} with **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.pool.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', highest_bid[0].id
            )
            if money >= highest_bid[1]:
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"-$1, "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                    highest_bid[1],
                    highest_bid[0].id,
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"{highest_bid[0].mention} spent the money in the meantime... Meh! Noone gets it then, pah!\nThis incident has been reported and they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                [u.id for u in raid.keys()],
            )
            await ctx.send(
                f"**Gave ${cash} of Atheistus' ${int(hp / 4)} drop to all survivors! Thanks to you, the world can live in peace and love again.**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Atheistus within 45 Minutes... He disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.deny_sending
        )

    @is_god()
    @commands.command()
    @locale_doc
    async def gambitspawn(self, ctx):
        """[Gambit only] Starts a raid."""
        await self.bot.session.get(
            "https://raid.travitia.xyz/toggle",
            headers={"Authorization": self.bot.config.raidauth},
        )
        await ctx.channel.set_permissions(
            ctx.guild.default_role, overwrite=self.read_only
        )
        await ctx.send(
            """
Gambit invites you to play a game. Inside this castle are rewards beyond your imagination, however all fun comes at a price. Inside lie countless tricks and traps. Take the risk and you could come out with riches beyond your imagination--however, be wary, as a wrong turn or bad luck could cause you to lose this game... for good.

The game starts in 15 Minutes
Use https://raid.travitia.xyz/ to join the raid!

**Only followers of Gambit may join.**

Quick and ugly: <https://discordapp.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.travitia.xyz/callback>
""",
            file=discord.File("assets/other/gambit.jpg"),
        )
        if not self.bot.config.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**The game starts in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**The game starts in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**The game starts in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**The game starts in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**The game starts in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**The game starts in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send("**Let the game begin! Fetching participant data... Hang on!**")

        async with self.bot.session.get(
            "https://raid.travitia.xyz/joined",
            headers={"Authorization": self.bot.config.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            dmgs = await conn.fetch(
                'SELECT p."user", p.class, ai.damage, p.atkmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Sword",
                raid_raw,
                "Gambit",
            )
            deffs = await conn.fetch(
                'SELECT p."user", p.class, ai.armor, p.defmultiply FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=ANY($2) AND type=$1 AND p.god=$3;',
                "Shield",
                raid_raw,
                "Gambit",
            )
        raid = {}
        for i in raid_raw:
            u = await self.bot.get_user_global(i)
            if not u:
                continue
            j = next(filter(lambda x: x["user"] == i, dmgs), None)
            if j is None:
                continue
            dmg = j["damage"] if j else 0
            j = next(filter(lambda x: x["user"] == i, deffs), None)
            if j is None:
                continue
            deff = j["armor"] if j else 0
            dmg, deff = await self.bot.generate_stats(i, dmg, deff)
            raid[u] = {"hp": 1000, "armor": deff, "damage": dmg}

        await ctx.send(
            "**Done getting data! Setting up castle and backend... The game will start in your DMs**"
        )

        castle = Castle(self.bot)
        for user, stats in raid.items():
            castle.add_player(Player(user, stats))

        await castle.run()

    def getpriceto(self, level: float):
        return sum(i * 25000 for i in range(1, int(level * 10) - 9))

    @commands.group(invoke_without_command=True)
    @locale_doc
    async def increase(self, ctx):
        _("""Upgrade your raid damage or defense multiplier.""")
        await ctx.send(
            _(
                "Use `{prefix}increase damage/defense` to upgrade your raid damage/defense multiplier by 10%."
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @increase.command()
    @locale_doc
    async def damage(self, ctx):
        _("""Increase your raid damage.""")
        newlvl = ctx.character_data["atkmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                _(
                    "Upgrading your weapon attack raid multiplier to {newlvl} costs **${price}**, you are too poor."
                ).format(newlvl=newlvl, price=price)
            )
        await self.bot.pool.execute(
            'UPDATE profile SET "atkmultiply"=$1, "money"="money"-$2 WHERE "user"=$3;',
            newlvl,
            price,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "You upgraded your weapon attack raid multiplier to {newlvl} for **${price}**."
            ).format(newlvl=newlvl, price=price)
        )

    @has_char()
    @increase.command()
    @locale_doc
    async def defense(self, ctx):
        _("""Increase your raid defense.""")
        newlvl = ctx.character_data["defmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                _(
                    "Upgrading your shield defense raid multiplier to {newlvl} costs **${price}**, you are too poor."
                ).format(newlvl=newlvl, price=price)
            )
        await self.bot.pool.execute(
            'UPDATE profile SET "defmultiply"=$1, "money"="money"-$2 WHERE "user"=$3;',
            newlvl,
            price,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "You upgraded your shield defense raid multiplier to {newlvl} for **${price}**."
            ).format(newlvl=newlvl, price=price)
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def raidstats(self, ctx):
        _("""View your raid stats.""")
        atk = ctx.character_data["atkmultiply"]
        deff = ctx.character_data["defmultiply"]
        atkp = self.getpriceto(atk + Decimal("0.1"))
        deffp = self.getpriceto(deff + Decimal("0.1"))
        if self.bot.in_class_line(ctx.character_data["class"], "Raider"):
            tier = self.bot.get_class_grade_from(ctx.character_data["class"], "Raider")
            atk += Decimal("0.1") * tier
            deff += Decimal("0.1") * tier
        await ctx.send(
            _(
                "**{author}'s raid multipliers**\nDamage Multiplier: x{atk} (Upgrading: ${atkp})\nDefense Multiplier: x{deff} (Upgrading: ${deffp})"
            ).format(
                author=ctx.author.mention, atk=atk, atkp=atkp, deff=deff, deffp=deffp
            )
        )

    @commands.command()
    @locale_doc
    async def raid(self, ctx):
        await ctx.send(
            _(
                "Did you ever want to join together with other players to defeat the dragon that roams this land? Raids got you covered!\nJoin the support server (`{prefix}support`) for more information."
            ).format(prefix=ctx.prefix)
        )


def setup(bot):
    bot.add_cog(Raid(bot))
