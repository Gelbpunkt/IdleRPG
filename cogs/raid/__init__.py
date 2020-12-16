"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

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
import re

from decimal import Decimal

import discord

from discord.ext import commands

from classes.classes import Raider
from classes.classes import from_string as class_from_string
from classes.converters import IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import random
from utils.checks import AlreadyRaiding, has_char, is_gm, is_god
from utils.i18n import _, locale_doc


def raid_channel():
    def predicate(ctx):
        return ctx.channel.id == 506_133_354_874_404_874

    return commands.check(predicate)


def raid_free():
    async def predicate(ctx):
        ttl = await ctx.bot.redis.execute("TTL", "special:raid")
        if ttl != -2:
            raise AlreadyRaiding("There is already a raid ongoing.")
        return True

    return commands.check(predicate)


def is_cm():
    def predicate(ctx) -> bool:
        return (
            ctx.guild.id == ctx.bot.config.game.support_server_id
            and 491353140042530826 in [r.id for r in ctx.author.roles]
        )

    return commands.check(predicate)


class Raid(commands.Cog):
    """Raids are only available in the support server. Use the support command for an invite link."""

    def __init__(self, bot):
        self.bot = bot

        self.boss = None
        self.allow_sending = discord.PermissionOverwrite(
            send_messages=True, read_messages=True
        )
        self.deny_sending = discord.PermissionOverwrite(
            send_messages=False, read_messages=False
        )
        self.read_only = discord.PermissionOverwrite(
            send_messages=False, read_messages=True
        )

    def getfinaldmg(self, damage: Decimal, defense):
        return v if (v := damage - defense) > 0 else 0

    async def set_raid_timer(self):
        await self.bot.redis.execute(
            "SET",
            "special:raid",
            "running",  # ctx isn't available
            "EX",
            3600,  # signup period + time until timeout
        )

    async def clear_raid_timer(self):
        await self.bot.redis.execute("DEL", "special:raid")

    @is_gm()
    @commands.command(hidden=True)
    async def alterraid(self, ctx, newhp: IntGreaterThan(0)):
        """[Bot Admin only] Change a raid boss' HP."""
        if not self.boss:
            return await ctx.send("No Boss active!")
        self.boss.update(hp=newhp, initial_hp=newhp)
        try:
            spawnmsg = await ctx.channel.fetch_message(self.boss["message"])
            edited_embed = spawnmsg.embeds[0]
            edited_embed.description = re.sub(
                r"\d+(,*\d)+ HP", f"{newhp:,.0f} HP", edited_embed.description
            )
            edited_embed.set_image(url="attachment://dragon.jpg")
            await spawnmsg.edit(embed=edited_embed)
        except discord.NotFound:
            return await ctx.send("Could not edit Boss HP!")
        await ctx.send("Boss HP updated!")

    @is_gm()
    @raid_channel()
    @raid_free()
    @commands.command(hidden=True, brief=_("Start a Zerekiel raid"))
    async def spawn(self, ctx, hp: IntGreaterThan(0)):
        """[Bot Admin only] Starts a raid."""
        await self.set_raid_timer()
        await self.bot.session.get(
            "https://raid.idlerpg.xyz/toggle",
            headers={"Authorization": self.bot.config.external.raidauth},
        )
        role = discord.utils.get(ctx.guild.roles, name="Ruby Donators")
        role2 = discord.utils.get(ctx.guild.roles, name="Diamond Donators")
        users = [u.id for u in role.members + role2.members]
        await self.bot.session.post(
            "https://raid.idlerpg.xyz/autosignup",
            headers={"Authorization": self.bot.config.external.raidauth},
            json={"users": users},
        )
        self.boss = {"hp": hp, "initial_hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.read_only,
        )

        fi = discord.File("assets/other/dragon.jpg")
        em = discord.Embed(
            title="Zerekiel Spawned",
            url="https://raid.travitia.xyz",
            description=(
                f"This boss has {self.boss['hp']:,.0f} HP and has high-end loot!\nThe"
                " evil dragon will be vulnerable in 15 Minutes\n\nUse"
                " https://raid.idlerpg.xyz/ to join the raid!\n\nFor a quick and ugly"
                " join [click"
                " here](https://discord.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.idlerpg.xyz/callback)!"
            ),
            color=self.bot.config.game.primary_colour,
        )
        em.set_image(url="attachment://dragon.jpg")
        em.set_thumbnail(url=ctx.author.avatar_url)

        spawnmsg = await ctx.send(embed=em, file=fi)
        self.boss.update(message=spawnmsg.id)

        if not self.bot.config.bot.is_beta:
            summary_channel = self.bot.get_channel(506_167_065_464_406_041)
            raid_ping = await summary_channel.send(
                "@everyone Zerekiel spawned! 15 Minutes until he is vulnerable...\nUse"
                " https://raid.idlerpg.xyz/ to join the raid!"
            )
            try:
                await raid_ping.publish()
            except discord.Forbidden:
                await summary_channel.send(
                    "Error! Couldn't publish message. Please publish manually"
                    f" {ctx.author.mention}"
                )
            else:
                await summary_channel.send(
                    "Message has been published!", delete_after=10
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
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**The dragon is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.idlerpg.xyz/joined",
            headers={"Authorization": self.bot.config.external.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            raid = {}
            for i in raid_raw:
                u = await self.bot.get_user_global(i)
                if not u:
                    continue
                if not (profile := await self.bot.cache.get_profile(u.id, conn=conn)):
                    continue
                dmg, deff = await self.bot.get_raidstats(
                    u,
                    atkmultiply=profile["atkmultiply"],
                    defmultiply=profile["defmultiply"],
                    classes=profile["class"],
                    race=profile["race"],
                    guild=profile["guild"],
                    conn=conn,
                )
                raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        raiders_joined = len(raid)
        await ctx.send(f"**Done getting data! {raiders_joined} Raiders joined.**")
        start = datetime.datetime.utcnow()

        while (
            self.boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))  # the guy it will attack
            dmg = random.randint(
                self.boss["min_dmg"], self.boss["max_dmg"]
            )  # effective damage the dragon does
            finaldmg = self.getfinaldmg(dmg, raid[target]["armor"])
            raid[target]["hp"] -= finaldmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xffb900,
                )
            else:
                em = discord.Embed(
                    title="Zerekiel attacked!",
                    description=f"{target} died!",
                    colour=0xffb900,
                )
            em.add_field(
                name="Theoretical Damage", value=finaldmg + raid[target]["armor"]
            )
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=finaldmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/dragon.jpg")
            await ctx.send(target.mention, embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            self.boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Zerekiel!", colour=0xff5c00)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/knight.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if self.boss["hp"] > 0:
                em.add_field(name="HP left", value=self.boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(embed=em)
            await asyncio.sleep(4)

        if len(raid) == 0:
            m = await ctx.send("The raid was all wiped!")
            await m.add_reaction("\U0001F1EB")
            summary_text = (
                "Emoji_here The raid was all wiped! Zerekiel had"
                f" **{self.boss['hp']:,.3f}** health remaining. Better luck next time."
            )
        elif self.boss["hp"] < 1:
            raid_duration = datetime.datetime.utcnow() - start
            minutes = (raid_duration.seconds % 3600) // 60
            seconds = raid_duration.seconds % 60
            summary_duration = f"{minutes} minutes, {seconds} seconds"

            await ctx.channel.set_permissions(
                ctx.guild.get_role(self.bot.config.game.member_role),
                overwrite=self.allow_sending,
            )
            highest_bid = [
                356_091_260_429_402_122,
                0,
            ]  # userid, amount

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
                    msg.author.id == highest_bid[0]
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a"
                " <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest"
                " bid for it wins <:roosip:505447694408482846>\nSimply type how much"
                " you bid!"
            )
            for p in page.pages:
                await ctx.send(p[4:-4])

            while True:
                try:
                    msg = await self.bot.wait_for("message", timeout=60, check=check)
                except asyncio.TimeoutError:
                    break
                bid = int(msg.content)
                money = await self.bot.cache.get_profile_col(msg.author.id, "money")
                if money and money >= bid:
                    highest_bid = [msg.author.id, bid]
                    await ctx.send(f"{msg.author.mention} bids **${msg.content}**!")
            msg = await ctx.send(
                f"Auction done! Winner is <@{highest_bid[0]}> with"
                f" **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.cache.get_profile_col(highest_bid[0], "money")
            if money >= highest_bid[1]:
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"-$1,'
                        ' "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                        highest_bid[1],
                        highest_bid[0],
                    )
                    await self.bot.log_transaction(
                        ctx,
                        from_=highest_bid[0],
                        to=2,
                        subject="money",
                        data={"Amount": highest_bid[1]},
                        conn=conn,
                    )
                await self.bot.cache.update_profile_cols_rel(
                    highest_bid[0], money=-highest_bid[1], crates_legendary=1
                )
                await msg.edit(content=f"{msg.content} Done!")
                summary_crate = (
                    "Emoji_here Legendary crate <:CrateLegendary:598094865678598144> "
                    f"sold to: **<@{highest_bid[0]}>** for **${highest_bid[1]:,.0f}**"
                )
            else:
                await ctx.send(
                    f"<@{highest_bid[0]}> spent the money in the meantime... Meh!"
                    " Noone gets it then, pah!\nThis incident has been reported and"
                    " they will get banned if it happens again. Cheers!"
                )
                summary_crate = (
                    "Emoji_here The Legendary Crate was not given to anyone since the"
                    f" supposed winning bidder <@{highest_bid[0]}> spent the money in"
                    " the meantime. They will get banned if it happens again."
                )

            cash_pool = int(self.boss["initial_hp"] / 4)
            survivors = len(raid)
            cash = int(cash_pool / survivors)  # what da hood gets per survivor
            users = [u.id for u in raid]
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=ANY($2);',
                cash,
                users,
            )
            for user in users:
                await self.bot.cache.update_profile_cols_rel(user, money=cash)
            await ctx.send(
                f"**Gave ${cash:,.0f} of the Zerekiel's ${cash_pool:,.0f} drop to all"
                " survivors!**"
            )

            summary_text = (
                f"Emoji_here Defeated in: **{summary_duration}**\n"
                f"{summary_crate}\n"
                f"Emoji_here Payout per survivor: **${cash:,.0f}**\n"
                f"Emoji_here Survivors: **{survivors}**"
            )

        else:
            m = await ctx.send(
                "The raid did not manage to kill Zerekiel within 45 Minutes... He"
                " disappeared!"
            )
            await m.add_reaction("\U0001F1EB")
            summary_text = (
                "Emoji_here The raid did not manage to kill Zerekiel within 45"
                f" Minutes... He disappeared with **{self.boss['hp']:,.3f}** health"
                " remaining."
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.deny_sending,
        )
        await self.clear_raid_timer()

        if not self.bot.config.bot.is_beta:
            summary = (
                "**Raid result:**\n"
                f"Emoji_here Health: **{self.boss['initial_hp']:,.0f}**\n"
                f"{summary_text}\n"
                f"Emoji_here Raiders joined: **{raiders_joined}**"
            )
            summary = summary.replace(
                "Emoji_here",
                ":small_blue_diamond:" if self.boss["hp"] < 1 else ":vibration_mode:",
            )
            summary_msg = await summary_channel.send(summary)
            try:
                await summary_msg.publish()
            except discord.Forbidden:
                await summary_channel.send(
                    "Error! Couldn't publish message. Please publish manually"
                    f" {ctx.author.mention}"
                )
            else:
                await summary_channel.send(
                    "Message has been published!", delete_after=10
                )

        self.boss = None

    @is_god()
    @raid_free()
    @commands.command(hidden=True, brief=_("Start a Kvothe raid"))
    async def kvothespawn(self, ctx, scrael: IntGreaterThan(1)):
        """[Kvothe only] Starts a raid."""
        await self.set_raid_timer()
        await self.bot.session.get(
            "https://raid.idlerpg.xyz/toggle",
            headers={"Authorization": self.bot.config.external.raidauth},
        )
        scrael = [{"hp": random.randint(80, 100), "id": i + 1} for i in range(scrael)]
        await ctx.send(
            """
The cthae has gathered an army of scrael. Fight for your life!

Use https://raid.idlerpg.xyz/ to join the raid!
**Only Kvothe's followers may join.**

Quick and ugly: <https://discord.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.idlerpg.xyz/callback>
""",
            file=discord.File("assets/other/cthae.jpg"),
        )
        if not self.bot.config.bot.is_beta:
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
            "https://raid.idlerpg.xyz/joined",
            headers={"Authorization": self.bot.config.external.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            raid = {}
            for i in raid_raw:
                u = await self.bot.get_user_global(i)
                if not u:
                    continue
                if (
                    not (profile := await self.bot.cache.get_profile(u.id, conn=conn))
                    or profile["god"] != "Kvothe"
                ):
                    continue
                try:
                    dmg, deff = await self.bot.get_raidstats(
                        u,
                        atkmultiply=profile["atkmultiply"],
                        defmultiply=profile["defmultiply"],
                        classes=profile["class"],
                        race=profile["race"],
                        guild=profile["guild"],
                        god=profile["god"],
                        conn=conn,
                    )
                except ValueError:
                    continue
                raid[u] = {"hp": 100, "armor": deff, "damage": dmg, "kills": 0}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            len(scrael) > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target, target_data = random.choice(list(raid.items()))
            dmg = random.randint(35, 65)
            dmg = self.getfinaldmg(
                dmg, target_data["armor"] * Decimal(random.choice(["0.4", "0.5"]))
            )
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
                    value=(
                        f"Is attacking the scrael and dealt `{target_data['damage']}`"
                        " damage"
                    ),
                )
            else:
                money = random.randint(250, 750)
                await self.bot.pool.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    target.id,
                )
                await self.bot.cache.update_profile_cols_rel(target.id, money=money)
                scrael.pop(0)
                em.add_field(
                    name="Hero attack", value=f"Killed the scrael and received ${money}"
                )
                if raid.get(target, None):
                    raid[target]["kills"] += 1
            em.set_image(url=f"{self.bot.BASE_URL}/swordsman2.jpg")
            await ctx.send(embed=em)
            await asyncio.sleep(7)

        if len(scrael) == 0:
            most_kills = sorted(raid.items(), key=lambda x: -(x[1]["kills"]))[0][0]
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "crates_legendary"="crates_legendary"+$1 WHERE'
                    ' "user"=$2;',
                    1,
                    most_kills.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=most_kills.id,
                    subject="crates",
                    data={"Rarity": "legendary", "Amount": 1},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(
                most_kills.id, crates_legendary=1
            )
            await ctx.send(
                "The scrael were defeated! Our most glorious hero,"
                f" {most_kills.mention}, has received Kvothe's grace, a"
                f" {self.bot.cogs['Crates'].emotes.legendary}."
            )
        elif len(raid) == 0:
            await ctx.send(
                "The scrael have extinguished life in Kvothe's temple! All heroes died!"
            )
        await self.clear_raid_timer()

    @is_god()
    @raid_free()
    @commands.command(hidden=True, brief=_("Start an Eden raid"))
    async def edenspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Eden only] Starts a raid."""
        await self.set_raid_timer()
        await self.bot.session.get(
            "https://raid.idlerpg.xyz/toggle",
            headers={"Authorization": self.bot.config.external.raidauth},
        )
        self.boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.read_only,
        )
        await ctx.send(
            f"""
The guardian of the gate to the garden has awoken! To gain entry to the Garden of Sanctuary that lays behind the gate you must defeat the guardian.
This boss has {self.boss['hp']} HP and will be vulnerable in 15 Minutes
Use https://raid.idlerpg.xyz/ to join the raid!
**Only followers of Eden may join.**
Quick and ugly: <https://discord.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.idlerpg.xyz/callback>
""",
            file=discord.File("assets/other/guardian.jpg"),
        )
        if not self.bot.config.bot.is_beta:
            await asyncio.sleep(300)
            await ctx.send("**The guardian will be vulnerable in 10 minutes**")
            await asyncio.sleep(300)
            await ctx.send("**The guardian will be vulnerable in 5 minutes**")
            await asyncio.sleep(180)
            await ctx.send("**The guardian will be vulnerable in 2 minutes**")
            await asyncio.sleep(60)
            await ctx.send("**The guardian will be vulnerable in 1 minute**")
            await asyncio.sleep(30)
            await ctx.send("**The guardian will be vulnerable in 30 seconds**")
            await asyncio.sleep(20)
            await ctx.send("**The guardian will be vulnerable in 10 seconds**")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(60)
        await ctx.send(
            "**The guardian is vulnerable! Fetching participant data... Hang on!**"
        )

        async with self.bot.session.get(
            "https://raid.idlerpg.xyz/joined",
            headers={"Authorization": self.bot.config.external.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            raid = {}
            for i in raid_raw:
                u = await self.bot.get_user_global(i)
                if not u:
                    continue
                if (
                    not (profile := await self.bot.cache.get_profile(u.id, conn=conn))
                    or profile["god"] != "Eden"
                ):
                    continue
                try:
                    dmg, deff = await self.bot.get_raidstats(
                        u,
                        atkmultiply=profile["atkmultiply"],
                        defmultiply=profile["defmultiply"],
                        classes=profile["class"],
                        race=profile["race"],
                        guild=profile["guild"],
                        god=profile["god"],
                        conn=conn,
                    )
                except ValueError:
                    continue
                raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            self.boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))  # the guy it will attack
            dmg = random.randint(self.boss["min_dmg"], self.boss["max_dmg"])
            dmg = self.getfinaldmg(dmg, raid[target]["armor"])
            raid[target]["hp"] -= dmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="The Guardian attacks the seekers of the garden!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xffb900,
                )
            else:
                em = discord.Embed(
                    title="The Guardian attacks the seekers of the garden!",
                    description=f"{target} died!",
                    colour=0xffb900,
                )
            em.add_field(name="Theoretical Damage", value=dmg + raid[target]["armor"])
            em.add_field(name="Shield", value=raid[target]["armor"])
            em.add_field(name="Effective Damage", value=dmg)
            em.set_author(name=str(target), icon_url=target.avatar_url)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/guardian_small.jpg")
            await ctx.send(embed=em)
            if raid[target]["hp"] <= 0:
                del raid[target]
            dmg_to_take = sum(i["damage"] for i in raid.values())
            self.boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(
                title="The seekers attacked the Guardian!", colour=0xff5c00
            )
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/eden_followers.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if self.boss["hp"] > 0:
                em.add_field(name="HP left", value=self.boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(embed=em)
            await asyncio.sleep(4)

        if len(raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif self.boss["hp"] < 1:
            await ctx.channel.set_permissions(
                ctx.guild.get_role(self.bot.config.game.member_role),
                overwrite=self.allow_sending,
            )
            winner = random.choice(list(raid.keys()))
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_legendary"="crates_legendary"+1 WHERE'
                ' "user"=$1;',
                winner.id,
            )
            await self.bot.cache.update_profile_cols_rel(winner.id, crates_legendary=1)
            await ctx.send(
                "The guardian was defeated, the seekers can enter the garden! Eden has"
                f" gracefully given {winner.mention} a legendary crate for their"
                " efforts."
            )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            users = [u.id for u in raid]
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                users,
            )
            for user in users:
                await self.bot.cache.update_profile_cols_rel(user, money=cash)
            await ctx.send(
                f"**Gave ${cash} of the Guardian's ${int(hp / 4)} drop to all"
                " survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill the Guardian within 45 Minutes... The"
                " entrance remains blocked!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.deny_sending,
        )
        await self.clear_raid_timer()
        self.boss = None

    @is_god()
    @raid_free()
    @commands.command(hidden=True, brief=_("Start a CHamburr raid"))
    async def chamburrspawn(self, ctx, hp: IntGreaterThan(0)):
        """[CHamburr only] Starts a raid."""
        await self.set_raid_timer()
        await self.bot.session.get(
            "https://raid.idlerpg.xyz/toggle",
            headers={"Authorization": self.bot.config.external.raidauth},
        )
        self.boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.read_only,
        )
        await ctx.send(
            f"""
*Time to eat the hamburger! No, this time, the hamburger will eat you up...*

This boss has {self.boss['hp']} HP and has high-end loot!
The hamburger will be vulnerable in 15 Minutes
Use https://raid.idlerpg.xyz/ to join the raid!
**Only followers of CHamburr may join.**

Quick and ugly: <https://discord.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.idlerpg.xyz/callback>
""",
            file=discord.File("assets/other/hamburger.jpg"),
        )
        if not self.bot.config.bot.is_beta:
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
            "https://raid.idlerpg.xyz/joined",
            headers={"Authorization": self.bot.config.external.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            raid = {}
            for i in raid_raw:
                u = await self.bot.get_user_global(i)
                if not u:
                    continue
                if (
                    not (profile := await self.bot.cache.get_profile(u.id, conn=conn))
                    or profile["god"] != "CHamburr"
                ):
                    continue
                try:
                    dmg, deff = await self.bot.get_raidstats(
                        u,
                        atkmultiply=profile["atkmultiply"],
                        defmultiply=profile["defmultiply"],
                        classes=profile["class"],
                        race=profile["race"],
                        guild=profile["guild"],
                        god=profile["god"],
                        conn=conn,
                    )
                except ValueError:
                    continue
                raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            self.boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))  # the guy it will attack
            dmg = random.randint(self.boss["min_dmg"], self.boss["max_dmg"])
            dmg = self.getfinaldmg(dmg, raid[target]["armor"])
            raid[target]["hp"] -= dmg  # damage dealt
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Hamburger attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xffb900,
                )
            else:
                em = discord.Embed(
                    title="Hamburger attacked!",
                    description=f"{target} died!",
                    colour=0xffb900,
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
            self.boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(
                title="The raid attacked the hamburger!", colour=0xff5c00
            )
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/knight.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if self.boss["hp"] > 0:
                em.add_field(name="HP left", value=self.boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(embed=em)
            await asyncio.sleep(4)

        if len(raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif self.boss["hp"] < 1:
            await ctx.channel.set_permissions(
                ctx.guild.get_role(self.bot.config.game.member_role),
                overwrite=self.allow_sending,
            )
            highest_bid = [
                356_091_260_429_402_122,
                0,
            ]  # userid, amount

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
                    msg.author.id == highest_bid[0]
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a"
                " <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest"
                " bid for it wins <:roosip:505447694408482846>\nSimply type how much"
                " you bid!"
            )
            for p in page.pages:
                await ctx.send(p[4:-4])

            while True:
                try:
                    msg = await self.bot.wait_for("message", timeout=60, check=check)
                except asyncio.TimeoutError:
                    break
                bid = int(msg.content)
                money = await self.bot.cache.get_profile_col(msg.author.id, "money")
                if money and money >= bid:
                    highest_bid = [msg.author.id, bid]
                    await ctx.send(f"{msg.author.mention} bids **${msg.content}**!")
            msg = await ctx.send(
                f"Auction done! Winner is <@{highest_bid[0]}> with"
                f" **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.cache.get_profile_col(highest_bid[0], "money")
            if money >= highest_bid[1]:
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"-$1,'
                        ' "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                        highest_bid[1],
                        highest_bid[0],
                    )
                    await self.bot.log_transaction(
                        ctx,
                        from_=highest_bid[0],
                        to=2,
                        subject="money",
                        data={"Amount": highest_bid[1]},
                        conn=conn,
                    )
                await self.bot.cache.update_profile_cols_rel(
                    highest_bid[0], money=-highest_bid[1], crates_legendary=1
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"<@{highest_bid[0]}> spent the money in the meantime... Meh!"
                    " Noone gets it then, pah!\nThis incident has been reported and"
                    " they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            users = [u.id for u in raid]
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                users,
            )
            for user in users:
                await self.bot.cache.update_profile_cols_rel(user, money=cash)
            await ctx.send(
                f"**Gave ${cash} of the hamburger's ${int(hp / 4)} drop to all"
                " survivors!**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill the hamburger within 45 Minutes... He"
                " disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.deny_sending,
        )
        await self.clear_raid_timer()
        self.boss = None

    @is_god()
    @raid_free()
    @commands.command(hidden=True, brief=_("Start a Jesus raid"))
    async def jesusspawn(self, ctx, hp: IntGreaterThan(0)):
        """[Jesus only] Starts a raid."""
        await self.set_raid_timer()
        await self.bot.session.get(
            "https://raid.idlerpg.xyz/toggle",
            headers={"Authorization": self.bot.config.external.raidauth},
        )
        self.boss = {"hp": hp, "min_dmg": 100, "max_dmg": 500}
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.read_only,
        )
        await ctx.send(
            f"""
**Atheistus the Tormentor has returned to earth to punish humanity for their belief.**

This boss has {self.boss['hp']} HP and has high-end loot!
Atheistus will be vulnerable in 15 Minutes

Use https://raid.idlerpg.xyz/ to join the raid!
**Only followers of Jesus may join.**

Quick and ugly: <https://discord.com/oauth2/authorize?client_id=453963965521985536&scope=identify&response_type=code&redirect_uri=https://raid.idlerpg.xyz/callback>
""",
            file=discord.File("assets/other/atheistus.jpg"),
        )
        if not self.bot.config.bot.is_beta:
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
            "https://raid.idlerpg.xyz/joined",
            headers={"Authorization": self.bot.config.external.raidauth},
        ) as r:
            raid_raw = await r.json()
        async with self.bot.pool.acquire() as conn:
            raid = {}
            for i in raid_raw:
                u = await self.bot.get_user_global(i)
                if not u:
                    continue
                if (
                    not (profile := await self.bot.cache.get_profile(u.id, conn=conn))
                    or profile["god"] != "Jesus"
                ):
                    continue
                try:
                    dmg, deff = await self.bot.get_raidstats(u, god="Jesus", conn=conn)
                except ValueError:
                    continue
                raid[u] = {"hp": 250, "armor": deff, "damage": dmg}

        await ctx.send("**Done getting data!**")

        start = datetime.datetime.utcnow()

        while (
            self.boss["hp"] > 0
            and len(raid) > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=45)
        ):
            target = random.choice(list(raid.keys()))
            dmg = random.randint(self.boss["min_dmg"], self.boss["max_dmg"])
            dmg = self.getfinaldmg(dmg, raid[target]["armor"])
            raid[target]["hp"] -= dmg
            if raid[target]["hp"] > 0:
                em = discord.Embed(
                    title="Atheistus attacked!",
                    description=f"{target} now has {raid[target]['hp']} HP!",
                    colour=0xffb900,
                )
            else:
                em = discord.Embed(
                    title="Atheistus attacked!",
                    description=f"{target} died!",
                    colour=0xffb900,
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
            self.boss["hp"] -= dmg_to_take
            await asyncio.sleep(4)
            em = discord.Embed(title="The raid attacked Atheistus!", colour=0xff5c00)
            em.set_thumbnail(url=f"{self.bot.BASE_URL}/knight.jpg")
            em.add_field(name="Damage", value=dmg_to_take)
            if self.boss["hp"] > 0:
                em.add_field(name="HP left", value=self.boss["hp"])
            else:
                em.add_field(name="HP left", value="Dead!")
            await ctx.send(embed=em)
            await asyncio.sleep(4)

        if len(raid) == 0:
            await ctx.send("The raid was all wiped!")
        elif self.boss["hp"] < 1:
            await ctx.channel.set_permissions(
                ctx.guild.get_role(self.bot.config.game.member_role),
                overwrite=self.allow_sending,
            )
            highest_bid = [
                356_091_260_429_402_122,
                0,
            ]  # userid, amount

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
                    msg.author.id == highest_bid[0]
                ):  # don't allow a player to outbid themselves
                    return False
                return True

            page = commands.Paginator()
            for u in list(raid.keys()):
                page.add_line(u.mention)
            page.add_line(
                "The raid killed the boss!\nHe dropped a"
                " <:CrateLegendary:598094865678598144> Legendary Crate!\nThe highest"
                " bid for it wins <:roosip:505447694408482846>\nSimply type how much"
                " you bid!"
            )
            for p in page.pages:
                await ctx.send(p[4:-4])

            while True:
                try:
                    msg = await self.bot.wait_for("message", timeout=60, check=check)
                except asyncio.TimeoutError:
                    break
                bid = int(msg.content)
                money = await self.bot.cache.get_profile_col(msg.author.id, "money")
                if money and money >= bid:
                    highest_bid = [msg.author.id, bid]
                    await ctx.send(f"{msg.author.mention} bids **${msg.content}**!")
            msg = await ctx.send(
                f"Auction done! Winner is <@{highest_bid[0]}> with"
                f" **${highest_bid[1]}**!\nGiving Legendary Crate..."
            )
            money = await self.bot.cache.get_profile_col(highest_bid[0], "money")
            if money >= highest_bid[1]:
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE profile SET "money"="money"-$1,'
                        ' "crates_legendary"="crates_legendary"+1 WHERE "user"=$2;',
                        highest_bid[1],
                        highest_bid[0],
                    )
                    await self.bot.log_transaction(
                        ctx,
                        from_=highest_bid[0],
                        to=2,
                        subject="money",
                        data={"Amount": highest_bid[1]},
                        conn=conn,
                    )
                await self.bot.cache.update_profile_cols_rel(
                    highest_bid[0], money=-highest_bid[1], crates_legendary=1
                )
                await msg.edit(content=f"{msg.content} Done!")
            else:
                await ctx.send(
                    f"<@{highest_bid[0]}> spent the money in the meantime... Meh!"
                    " Noone gets it then, pah!\nThis incident has been reported and"
                    " they will get banned if it happens again. Cheers!"
                )

            cash = int(hp / 4 / len(raid))  # what da hood gets per survivor
            users = [u.id for u in raid]
            await self.bot.pool.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=ANY($2);',
                cash,
                users,
            )
            for user in users:
                await self.bot.cache.update_profile_cols_rel(user, money=cash)
            await ctx.send(
                f"**Gave ${cash} of Atheistus' ${int(hp / 4)} drop to all survivors!"
                " Thanks to you, the world can live in peace and love again.**"
            )

        else:
            await ctx.send(
                "The raid did not manage to kill Atheistus within 45 Minutes... He"
                " disappeared!"
            )

        await asyncio.sleep(30)
        await ctx.channel.set_permissions(
            ctx.guild.get_role(self.bot.config.game.member_role),
            overwrite=self.deny_sending,
        )
        await self.clear_raid_timer()
        self.boss = None

    def getpriceto(self, level: float):
        return sum(i * 25000 for i in range(1, int(level * 10) - 9))

    @commands.group(invoke_without_command=True, brief=_("Increase your raidstats"))
    @locale_doc
    async def increase(self, ctx):
        _(
            """Upgrade your raid damage or defense multiplier. These will affect your performance in raids and raidbattles."""
        )
        await ctx.send(
            _(
                "Use `{prefix}increase damage/defense` to upgrade your raid"
                " damage/defense multiplier by 10%."
            ).format(prefix=ctx.prefix)
        )

    @user_cooldown(60, identifier="increase")
    @has_char()
    @increase.command(brief=_("Upgrade your raid damage"))
    @locale_doc
    async def damage(self, ctx):
        _("""Increase your raid damage.""")
        newlvl = ctx.character_data["atkmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                _(
                    "Upgrading your weapon attack raid multiplier to {newlvl} costs"
                    " **${price}**, you are too poor."
                ).format(newlvl=newlvl, price=price)
            )
        if not await ctx.confirm(
            _(
                "Upgrading your weapon attack raid multiplier to {newlvl} costs"
                " **${price}**, proceed?"
            ).format(newlvl=newlvl, price=price)
        ):
            return
        async with self.bot.pool.acquire() as conn:
            if not await self.bot.has_money(ctx.author, price, conn=conn):
                return await ctx.send(
                    _(
                        "Upgrading your weapon attack raid multiplier to {newlvl} costs"
                        " **${price}**, you are too poor."
                    ).format(newlvl=newlvl, price=price)
                )
            await conn.execute(
                'UPDATE profile SET "atkmultiply"=$1, "money"="money"-$2 WHERE'
                ' "user"=$3;',
                newlvl,
                price,
                ctx.author.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="money",
                data={"Amount": price},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, atkmultiply=Decimal("0.1"), money=-price
        )
        await ctx.send(
            _(
                "You upgraded your weapon attack raid multiplier to {newlvl} for"
                " **${price}**."
            ).format(newlvl=newlvl, price=price)
        )

    @user_cooldown(60, identifier="increase")
    @has_char()
    @increase.command(brief=_("Upgrade your raid defense"))
    @locale_doc
    async def defense(self, ctx):
        _("""Increase your raid defense.""")
        newlvl = ctx.character_data["defmultiply"] + Decimal("0.1")
        price = self.getpriceto(newlvl)
        if ctx.character_data["money"] < price:
            return await ctx.send(
                _(
                    "Upgrading your shield defense raid multiplier to {newlvl} costs"
                    " **${price}**, you are too poor."
                ).format(newlvl=newlvl, price=price)
            )
        if not await ctx.confirm(
            _(
                "Upgrading your shield defense raid multiplier to {newlvl} costs"
                " **${price}**, proceed?"
            ).format(newlvl=newlvl, price=price)
        ):
            return
        async with self.bot.pool.acquire() as conn:
            if not await self.bot.has_money(ctx.author, price, conn=conn):
                return await ctx.send(
                    _(
                        "Upgrading your shield defense raid multiplier to {newlvl}"
                        " costs **${price}**, you are too poor."
                    ).format(newlvl=newlvl, price=price)
                )
            await conn.execute(
                'UPDATE profile SET "defmultiply"=$1, "money"="money"-$2 WHERE'
                ' "user"=$3;',
                newlvl,
                price,
                ctx.author.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=2,
                subject="money",
                data={"Amount": price},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, defmultiply=Decimal("0.1"), money=-price
        )
        await ctx.send(
            _(
                "You upgraded your shield defense raid multiplier to {newlvl} for"
                " **${price}**."
            ).format(newlvl=newlvl, price=price)
        )

    @has_char()
    @commands.command(brief=_("View your raid stats"))
    @locale_doc
    async def raidstats(self, ctx):
        _(
            """View your raidstats. These will affect your performance in raids and raidbattles."""
        )
        atk = ctx.character_data["atkmultiply"]
        deff = ctx.character_data["defmultiply"]
        atkp = self.getpriceto(atk + Decimal("0.1"))
        deffp = self.getpriceto(deff + Decimal("0.1"))
        classes = [class_from_string(c) for c in ctx.character_data["class"]]
        for c in classes:
            if c and c.in_class_line(Raider):
                tier = c.class_grade()
                atk += Decimal("0.1") * tier
                deff += Decimal("0.1") * tier
        if buildings := await self.bot.get_city_buildings(ctx.character_data["guild"]):
            atk += Decimal("0.1") * buildings["raid_building"]
            deff += Decimal("0.1") * buildings["raid_building"]
        await ctx.send(
            _(
                "**{author}'s raid multipliers**\nDamage Multiplier: x{atk} (Upgrading:"
                " ${atkp})\nDefense Multiplier: x{deff} (Upgrading: ${deffp})"
            ).format(
                author=ctx.author.mention, atk=atk, atkp=atkp, deff=deff, deffp=deffp
            )
        )

    @commands.command(brief=_("Did somebody say Raid?"))
    @locale_doc
    async def raid(self, ctx):
        _("""Informs you about joining raids.""")
        await ctx.send(
            _(
                "Did you ever want to join together with other players to defeat the"
                " dragon that roams this land? Raids got you covered!\nJoin the support"
                " server (`{prefix}support`) for more information."
            ).format(prefix=ctx.prefix)
        )


def setup(bot):
    bot.add_cog(Raid(bot))
