"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import datetime
import functools
from io import BytesIO

import discord
from async_timeout import timeout
from discord.ext import commands

from classes.converters import IntFromTo, MemberWithCharacter, User
from cogs.classes import genstats
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import checks
from utils import misc as rpgtools


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @user_cooldown(3600)
    @commands.command(
        aliases=["new", "c", "start"], description="Creates a new character."
    )
    async def create(self, ctx):
        if await checks.user_has_char(self.bot, ctx.author.id):
            return await ctx.send(
                f"You already own a character. Use `{ctx.prefix}profile` to view them!"
            )
        await ctx.send(
            "What shall your character's name be? (Minimum 3 Characters, Maximum 20)"
        )

        def mycheck(amsg):
            return amsg.author == ctx.author

        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(
                f"Timeout expired. Enter `{ctx.prefix}{ctx.command}` again to retry!"
            )
        name = name.content.strip()
        if len(name) > 2 and len(name) < 21:
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO profile VALUES ($1, $2, $3, $4);",
                    ctx.author.id,
                    name,
                    100,
                    0,
                )
                itemid = await conn.fetchval(
                    "INSERT INTO allitems (owner, name, value, type, damage, armor) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;",
                    ctx.author.id,
                    "Starter Sword",
                    0,
                    "Sword",
                    3.0,
                    0.0,
                )
                await conn.execute(
                    "INSERT INTO inventory (item, equipped) VALUES ($1, $2);",
                    itemid,
                    True,
                )
                itemid = await conn.fetchval(
                    "INSERT INTO allitems (owner, name, value, type, damage, armor) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;",
                    ctx.author.id,
                    "Starter Shield",
                    0,
                    "Shield",
                    0.0,
                    3.0,
                )
                await conn.execute(
                    "INSERT INTO inventory (item, equipped) VALUES ($1, $2);",
                    itemid,
                    True,
                )
            await ctx.send(
                f"Successfully added your character **{name}**! Now use `{ctx.prefix}profile` to view your character!"
            )
        elif len(name) < 3:
            await ctx.send("Character names must be at least 3 characters!")
            await self.bot.reset_cooldown(ctx)
        elif len(name) > 20:
            await ctx.send("Character names mustn't exceed 20 characters!")
            await self.bot.reset_cooldown(ctx)
        else:
            await ctx.send(
                "An unknown error occured while checking your name. Try again!"
            )

    @commands.command(
        aliases=["me", "p"], description="View your or a different user's profile."
    )
    async def profile(self, ctx, *, person: User = None):
        await ctx.trigger_typing()
        person = person or ctx.author
        targetid = person.id
        async with self.bot.pool.acquire() as conn:
            profile = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', targetid
            )
            if not profile:
                return await ctx.send(f"**{person}** does not have a character.")
            sword, shield = await self.bot.get_equipped_items_for(targetid)
            ranks = await self.bot.get_ranks_for(targetid)
            mission = await conn.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', targetid
            )
            guild = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', profile["guild"]
            )
            if mission:
                missionend = await conn.fetchval(
                    "SELECT $1-clock_timestamp();", mission["end"]
                )
            else:
                missionend = None
            background = profile["background"]
            if background == "0":
                background = "assets/profiles/Profile.png"
            else:
                async with timeout(10), self.bot.session.get(background) as r:
                    if r.status == 200:
                        background = BytesIO(await r.read())
                        background.seek(0)
                    else:
                        background = "assets/profiles/Profile.png"
            if profile["marriage"]:
                marriage = (await rpgtools.lookup(self.bot, profile["marriage"])).split(
                    "#"
                )[0]
            else:
                marriage = "Not married"

            sword = (
                [sword["name"], sword["damage"]] if sword else ["None equipped", 0.00]
            )
            shield = (
                [shield["name"], shield["armor"]] if shield else ["None equipped", 0.00]
            )

            damage, armor = await genstats(self.bot, targetid, sword[1], shield[1])
            damage -= sword[1]
            armor -= shield[1]
            extras = (damage, armor)

        thing = functools.partial(
            rpgtools.profile_image,
            profile,
            sword,
            shield,
            mission,
            missionend,
            ranks,
            profile["colour"],
            background,
            marriage,
            guild,
            extras,
        )
        output_buffer = await self.bot.loop.run_in_executor(None, thing)
        await ctx.send(file=discord.File(fp=output_buffer, filename="Profile.png"))

    @commands.command(aliases=["p2", "pp"])
    async def profile2(self, ctx, target: User = None):
        """View someone's profile, not image based."""
        target = target or ctx.author
        rank_money, rank_xp = await self.bot.get_ranks_for(target)
        sword, shield = await self.bot.get_equipped_items_for(target)
        async with self.bot.pool.acquire() as conn:
            p_data = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', target.id
            )
            if not p_data:
                return await ctx.send(f"**{target}** does not have a character.")
            mission = await conn.fetchrow(
                'SELECT *, "end" - clock_timestamp() AS timeleft FROM mission WHERE "name"=$1;',
                target.id,
            )
            guild = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', p_data["guild"]
            )
        try:
            colour = discord.Colour.from_rgb(*rpgtools.hex_to_rgb(p_data["colour"]))
        except ValueError:
            colour = 0x000000
        if mission:
            timeleft = (
                str(mission["timeleft"]).split(".")[0]
                if mission["end"] > datetime.datetime.now(datetime.timezone.utc)
                else "Finished"
            )
        sword = f"{sword['name']} - {sword['damage']}" if sword else "No sword"
        shield = f"{shield['name']} - {shield['armor']}" if shield else "No shield"
        level = rpgtools.xptolevel(p_data["xp"])
        em = discord.Embed(colour=colour, title=f"{target}: {p_data['name']}")
        em.set_thumbnail(url=target.avatar_url)
        em.add_field(
            name="General",
            value=f"**Money**: `${p_data['money']}`\n**Level**: `{level}`\n**Class**: `{p_data['class']}`\n**PvP Wins**: `{p_data['pvpwins']}`\n**Guild**: `{guild}`",
        )
        em.add_field(
            name="Ranks", value=f"**Richest**: `{rank_money}`\n**XP**: `{rank_xp}`"
        )
        em.add_field(name="Equipment", value=f"Sword: {sword}\nShield: {shield}")
        if mission:
            em.add_field(name="Mission", value=f"{mission['dungeon']} - {timeleft}")
        await ctx.send(embed=em)

    @checks.has_char()
    @commands.command(aliases=["money", "e"])
    async def economy(self, ctx):
        """Shows your balance."""
        await ctx.send(
            f"You currently have **${ctx.character_data['money']}**, {ctx.author.mention}!"
        )

    @checks.has_char()
    @commands.command()
    async def xp(self, ctx):
        """Shows your current XP and level."""
        points = ctx.character_data["xp"]
        await ctx.send(
            f"You currently have **{points} XP**, which means you are on Level **{rpgtools.xptolevel(points)}**. Missing to next level: **{rpgtools.xptonextlevel(points)}**"
        )

    def invembed(self, ctx, ret, currentpage, maxpage):
        result = discord.Embed(
            title=f"{ctx.author.display_name}'s inventory includes",
            colour=discord.Colour.blurple(),
        )
        for weapon in ret:
            if weapon[7]:
                eq = "(**Equipped**)"
            else:
                eq = ""
            statstr = (
                f"Damage: `{weapon[5]}`"
                if weapon[4] == "Sword"
                else f"Armor: `{weapon[6]}`"
            )
            result.add_field(
                name=f"{weapon[2]} {eq}",
                value=f"ID: `{weapon[0]}`, Type: `{weapon[4]}` with {statstr}. Value is **${weapon[3]}**",
            )
        result.set_footer(text=f"Page {currentpage + 1} of {maxpage + 1}")
        return result

    @checks.has_char()
    @commands.command(aliases=["inv", "i"])
    async def inventory(self, ctx):
        """Shows your current inventory."""
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT ai.*, i.equipped FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE p."user"=$1 ORDER BY i."equipped" DESC, ai."damage"+ai."armor" DESC;',
                ctx.author.id,
            )
        if not ret:
            return await ctx.send("Your inventory is empty.")
        allitems = list(chunks(ret, 5))
        maxpage = len(allitems) - 1
        embeds = [
            self.invembed(ctx, chunk, idx, maxpage)
            for idx, chunk in enumerate(allitems)
        ]
        await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @checks.has_char()
    @commands.command(aliases=["use"])
    async def equip(self, ctx, itemid: int):
        """Equips an item of yours by ID."""
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT ai.* FROM inventory i JOIN allitems ai ON (i."item"=ai."id") WHERE ai."owner"=$1 and ai."id"=$2;',
                ctx.author.id,
                itemid,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID `{itemid}`.")
            olditem = await conn.fetchrow(
                "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type=$2;",
                ctx.author.id,
                item["type"],
            )
            if olditem is not None:
                await conn.execute(
                    'UPDATE inventory SET "equipped"=False WHERE "item"=$1;',
                    olditem["id"],
                )
            await conn.execute(
                'UPDATE inventory SET "equipped"=True WHERE "item"=$1;', itemid
            )
            if olditem is not None:
                await ctx.send(
                    f"Successfully equipped item `{itemid}` and put off item `{olditem[0]}`."
                )
            else:
                await ctx.send(f"Successfully equipped item `{itemid}`.")

    @checks.has_char()
    @user_cooldown(3600)
    @commands.command()
    async def merge(self, ctx, firstitemid: int, seconditemid: int):
        """Merges two items to a better one. Second one is consumed."""
        if firstitemid == seconditemid:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send("Good luck with that.")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "id"=$1 AND "owner"=$2;',
                firstitemid,
                ctx.author.id,
            )
            item2 = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "id"=$1 AND "owner"=$2;',
                seconditemid,
                ctx.author.id,
            )
            if not item or not item2:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send("You don't own both of these items.")
            if item[4] == "Sword":
                stat1 = ("damage", item[5])
            elif item[4] == "Shield":
                stat1 = ("armor", item[6])
            if item2[4] == "Sword":
                stat2 = ("damage", item2[5])
            elif item2[4] == "Shield":
                stat2 = ("armor", item2[6])
            if stat2[1] < stat1[1] - 5 or stat2[1] > stat1[1] + 5:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    f"The seconds item's stat must be in the range of `{stat1[1] - 5}` to `{stat1[1] + 5}` to upgrade an item with the stat of `{stat1[1]}`."
                )
            if stat1[1] > 40:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    "This item is already on the maximum upgrade level."
                )
            await conn.execute(
                f'UPDATE allitems SET {stat1[0]}={stat1[0]}+1 WHERE "id"=$1;',
                firstitemid,
            )
            await conn.execute('DELETE FROM allitems WHERE "id"=$1;', seconditemid)
        await ctx.send(
            f"The {stat1[0]} of your **{item['name']}** is now **{stat1[1] + 1}**. The other item was destroyed."
        )

    @checks.has_char()
    @user_cooldown(3600)
    @commands.command(aliases=["upgrade"])
    async def upgradeweapon(self, ctx, itemid: int):
        """Upgrades an item's stat by 1."""
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "id"=$1 AND "owner"=$2;',
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID `{itemid}`.")
            if item["type"] == "Sword":
                stattoupgrade = "damage"
                pricetopay = int(item[5] * 250)
            elif item["type"] == "Shield":
                stattoupgrade = "armor"
                pricetopay = int(item[6] * 250)
            if int(item[stattoupgrade]) > 40:
                return await ctx.send(
                    "Your weapon already reached the maximum upgrade level."
                )
        if ctx.character_data["money"] < pricetopay:
            return await ctx.send(
                f"You are too poor to upgrade this item. The upgrade costs **${pricetopay}**, but you only have **${ctx.character_data['money']}**."
            )

        def check(m):
            return m.content.lower() == "confirm" and m.author == ctx.author

        await ctx.send(
            f"Are you sure? Type `confirm` to improve your weapon for **${pricetopay}**"
        )
        try:
            await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send("Weapon upgrade cancelled.")
        if not await checks.has_money(self.bot, ctx.author.id, pricetopay):
            return await ctx.send("You're too poor.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                f'UPDATE allitems SET {stattoupgrade}={stattoupgrade}+1 WHERE "id"=$1;',
                itemid,
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                pricetopay,
                ctx.author.id,
            )
        await ctx.send(
            f"The {stattoupgrade} of your **{item['name']}** is now **{int(item[stattoupgrade])+1}**. **${pricetopay}** has been taken off your balance."
        )

    @checks.has_char()
    @commands.command()
    async def give(
        self, ctx, money: IntFromTo(0, 100000000), other: MemberWithCharacter
    ):
        """Gift money!"""
        if other == ctx.author:
            return await ctx.send("No cheating!")
        if ctx.character_data["money"] < money:
            return await ctx.send("You are too poor.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
            )
        await ctx.send(f"Successfully gave **${money}** to {other.mention}.")

    @checks.has_char()
    @commands.command()
    async def rename(self, ctx):
        """Renames your character."""
        await ctx.send(
            "What shall your character's name be? (Minimum 3 Characters, Maximum 20)"
        )
        try:

            def mycheck(amsg):
                return amsg.author == ctx.author

            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
            name = name.content.strip()
            if len(name) > 2 and len(name) < 21:
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE profile SET "name"=$1 WHERE "user"=$2;',
                        name,
                        ctx.author.id,
                    )
                await ctx.send("Character name updated.")
            elif len(name) < 3:
                await ctx.send("Character names must be at least 3 characters!")
            elif len(name) > 20:
                await ctx.send("Character names mustn't exceed 20 characters!")
            else:
                await ctx.send(
                    "An unknown error occured while checking your name. Try again!"
                )
        except asyncio.TimeoutError:
            await ctx.send(
                f"Timeout expired. Enter `{ctx.prefix}{ctx.command}` again to retry!"
            )

    @checks.has_char()
    @commands.command(aliases=["rm", "del"])
    async def delete(self, ctx):
        """Deletes your character."""

        def mycheck(amsg):
            return (
                amsg.content.strip() == "deletion confirm" and amsg.author == ctx.author
            )

        await ctx.send(
            "Are you sure? Type `deletion confirm` in the next 15 seconds to confirm."
        )
        try:
            await self.bot.wait_for("message", timeout=15, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled deletion of your character.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute('DELETE FROM boosters WHERE "user"=$1;', ctx.author.id)
            g = await conn.fetchval(
                'DELETE FROM guild WHERE "leader"=$1 RETURNING id;', ctx.author.id
            )
            if g:
                await conn.execute(
                    'UPDATE profile SET "guildrank"=$1, "guild"=$2 WHERE "guild"=$3;',
                    "Member",
                    0,
                    g,
                )
            await conn.execute(
                'UPDATE profile SET "marriage"=$1 WHERE "marriage"=$2;',
                0,
                ctx.author.id,
            )
            await conn.execute(
                'DELETE FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
            )
            await conn.execute('DELETE FROM profile WHERE "user"=$1;', ctx.author.id)
        await ctx.send(
            "Successfully deleted your character. Sorry to see you go :frowning:"
        )

    @commands.command(aliases=["color"])
    async def colour(self, ctx, colour: str):
        """Sets your profile text colour."""
        if len(colour) != 7 or not colour.startswith("#"):
            return await ctx.send("Format for colour is `#RRGGBB`.")
        await self.bot.pool.execute(
            'UPDATE profile SET "colour"=$1 WHERE "user"=$2;', colour, ctx.author.id
        )
        await ctx.send(f"Successfully set your profile colour to `{colour}`.")


def setup(bot):
    bot.add_cog(Profile(bot))
