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
from io import BytesIO

import discord
from discord.ext import commands
from discord.ext.commands.default import Author

from classes.converters import IntFromTo, MemberWithCharacter, User
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import checks
from utils import misc as rpgtools


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @checks.has_no_char()
    @user_cooldown(3600)
    @commands.command(aliases=["new", "c", "start"])
    @locale_doc
    async def create(self, ctx):
        _("""Creates a new character.""")
        await ctx.send(
            _("What shall your character's name be? (Minimum 3 Characters, Maximum 20)")
        )

        def mycheck(amsg):
            return amsg.author == ctx.author and amsg.channel == ctx.channel

        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Timeout expired. Please retry!"))
        name = name.content
        if len(name) > 2 and len(name) < 21:
            await self.bot.pool.execute(
                "INSERT INTO profile VALUES ($1, $2, $3, $4);",
                ctx.author.id,
                name,
                100,
                0,
            )
            await self.bot.create_item(
                name=_("Starter Sword"),
                value=0,
                type_="Sword",
                damage=3.0,
                armor=0.0,
                owner=ctx.author,
                equipped=True,
            )
            await self.bot.create_item(
                name=_("Starter Shield"),
                value=0,
                type_="Shield",
                damage=0.0,
                armor=3.0,
                owner=ctx.author,
                equipped=True,
            )
            await ctx.send(
                _(
                    "Successfully added your character **{name}**! Now use `{prefix}profile` to view your character!"
                ).format(name=name, prefix=ctx.prefix)
            )
        elif len(name) < 3 or len(name) > 20:
            await ctx.send(
                _("Character names must be at least 3 characters and up to 20.")
            )
            await self.bot.reset_cooldown(ctx)

    @commands.command(aliases=["me", "p"])
    @locale_doc
    async def profile(self, ctx, *, person: User = Author):
        _("""View someone's or your own profile.""")
        await ctx.trigger_typing()
        targetid = person.id
        async with self.bot.pool.acquire() as conn:
            profile = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', targetid
            )
            if not profile:
                return await ctx.send(
                    _("**{person}** does not have a character.").format(person=person)
                )
            sword, shield = await self.bot.get_equipped_items_for(targetid)
            ranks = await self.bot.get_ranks_for(targetid)
            mission = await self.bot.get_adventure(targetid)
            guild = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', profile["guild"]
            )
            v1 = sword["damage"] if sword else 0.0
            v2 = shield["armor"] if shield else 0.0
            damage, armor = await self.bot.generate_stats(
                targetid, v1, v2, class_=profile["class"]
            )
            extras = (damage - v1, armor - v2)
            sworddmg = f"{v1}{' (+' + str(extras[0]) + ')' if extras[0] else ''}"
            shielddef = f"{v2}{' (+' + str(extras[1]) + ')' if extras[1] else ''}"
            async with self.bot.trusted_session.post(
                f"{self.bot.config.okapi_url}/api/genprofile",
                data={
                    "name": profile["name"],
                    "color": profile["colour"],
                    "image": profile["background"],
                    "money": f"{profile['money']}",
                    "pvpWins": f"{profile['pvpwins']}",
                    "ecoRank": f"{ranks[0]}",
                    "rank": f"{ranks[1]}",
                    "level": rpgtools.xptolevel(profile["xp"]),
                    "swordDamage": sworddmg,
                    "shieldDamage": shielddef,  # Dini you fucked up
                    "swordName": sword["name"] if sword else "None Equipped",
                    "shieldName": shield["name"] if shield else "None Equipped",
                    "married": await rpgtools.lookup(self.bot, profile["marriage"])
                    or _("Not Married"),
                    "guild": guild,
                    "class": profile["class"],
                    "icon": self.bot.get_class_line(profile["class"]).lower(),
                    "mission": f"{mission[0]} - {mission[1] if not mission[2] else _('Finished')}"
                    if mission
                    else _("No Mission"),
                },
            ) as req:
                img = BytesIO(await req.read())
        await ctx.send(file=discord.File(fp=img, filename="Profile.png"))

    @commands.command(aliases=["p2", "pp"])
    @locale_doc
    async def profile2(self, ctx, target: User = Author):
        _("""View someone's profile, not image based.""")
        rank_money, rank_xp = await self.bot.get_ranks_for(target)
        sword, shield = await self.bot.get_equipped_items_for(target)
        async with self.bot.pool.acquire() as conn:
            p_data = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', target.id
            )
            if not p_data:
                return await ctx.send(
                    _("**{target}** does not have a character.").format(target=target)
                )
            mission = await self.bot.get_adventure(target)
            guild = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', p_data["guild"]
            )
        try:
            colour = discord.Colour.from_rgb(*rpgtools.hex_to_rgb(p_data["colour"]))
        except ValueError:
            colour = 0x000000
        if mission:
            timeleft = str(mission[1]).split(".")[0] if not mission[2] else "Finished"
        sword = f"{sword['name']} - {sword['damage']}" if sword else "No sword"
        shield = f"{shield['name']} - {shield['armor']}" if shield else "No shield"
        level = rpgtools.xptolevel(p_data["xp"])
        em = discord.Embed(colour=colour, title=f"{target}: {p_data['name']}")
        em.set_thumbnail(url=target.avatar_url)
        em.add_field(
            name=_("General"),
            value=_(
                """\
**Money**: `${money}`
**Level**: `{level}`
**Class**: `{class_}`
**PvP Wins**: `{pvp}`
**Guild**: `{guild}`"""
            ).format(
                money=p_data["money"],
                level=level,
                class_=p_data["class"],
                pvp=p_data["pvpwins"],
                guild=guild,
            ),
        )
        em.add_field(
            name=_("Ranks"),
            value=_("**Richest**: `{rank_money}`\n**XP**: `{rank_xp}`").format(
                rank_money=rank_money, rank_xp=rank_xp
            ),
        )
        em.add_field(
            name=_("Equipment"),
            value=_("Sword: {sword}\nShield: {shield}").format(
                sword=sword, shield=shield
            ),
        )
        if mission:
            em.add_field(name=_("Mission"), value=f"{mission[0]} - {timeleft}")
        await ctx.send(embed=em)

    @checks.has_char()
    @commands.command(aliases=["money", "e"])
    @locale_doc
    async def economy(self, ctx):
        _("""Shows your balance.""")
        await ctx.send(
            _("You currently have **${money}**, {author}!").format(
                money=ctx.character_data["money"], author=ctx.author.mention
            )
        )

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def xp(self, ctx):
        _("""Shows your current XP and level.""")
        points = ctx.character_data["xp"]
        await ctx.send(
            _(
                "You currently have **{points} XP**, which means you are on Level **{level}**. Missing to next level: **{missing}**"
            ).format(
                points=points,
                level=rpgtools.xptolevel(points),
                missing=rpgtools.xptonextlevel(points),
            )
        )

    def invembed(self, ctx, ret, currentpage, maxpage):
        result = discord.Embed(
            title=_("{user}'s inventory includes").format(user=ctx.disp),
            colour=discord.Colour.blurple(),
        )
        for weapon in ret:
            if weapon[7]:
                eq = _("(**Equipped**)")
            else:
                eq = ""
            statstr = (
                _("Damage: `{damage}`").format(damage=weapon["damage"])
                if weapon[4] == "Sword"
                else _("Armor: `{armor}`").format(armor=weapon["armor"])
            )
            result.add_field(
                name=f"{weapon[2]} {eq}",
                value=_(
                    "ID: `{id}`, Type: `{type_}` with {statstr}. Value is **${value}**"
                ).format(
                    id=weapon["id"],
                    type_=weapon["type"],
                    statstr=statstr,
                    value=weapon["value"],
                ),
            )
        result.set_footer(
            text=_("Page {page} of {maxpages}").format(
                page=currentpage + 1, maxpages=maxpage + 1
            )
        )
        return result

    @checks.has_char()
    @commands.command(aliases=["inv", "i"])
    @locale_doc
    async def inventory(self, ctx):
        _("""Shows your current inventory.""")
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT ai.*, i.equipped FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE p."user"=$1 ORDER BY i."equipped" DESC, ai."damage"+ai."armor" DESC;',
                ctx.author.id,
            )
        if not ret:
            return await ctx.send(_("Your inventory is empty."))
        allitems = list(chunks(ret, 5))
        maxpage = len(allitems) - 1
        embeds = [
            self.invembed(ctx, chunk, idx, maxpage)
            for idx, chunk in enumerate(allitems)
        ]
        await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @checks.has_char()
    @commands.command(aliases=["use"])
    @locale_doc
    async def equip(self, ctx, itemid: int):
        _("""Equips an item of yours by ID.""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT ai.* FROM inventory i JOIN allitems ai ON (i."item"=ai."id") WHERE ai."owner"=$1 and ai."id"=$2;',
                ctx.author.id,
                itemid,
            )
            if not item:
                return await ctx.send(
                    _("You don't own an item with the ID `{itemid}`.").format(
                        itemid=itemid
                    )
                )
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
            if olditem:
                await ctx.send(
                    _(
                        "Successfully equipped item `{itemid}` and put off item `{olditem}`."
                    ).format(itemid=itemid, olditem=olditem["id"])
                )
            else:
                await ctx.send(_("Successfully equipped item `{itemid}`.").format(itemid=itemid))

    @checks.has_char()
    @user_cooldown(3600)
    @commands.command()
    @locale_doc
    async def merge(self, ctx, firstitemid: int, seconditemid: int):
        _("""Merges two items to a better one. Second one is consumed.""")
        if firstitemid == seconditemid:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Good luck with that."))
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
                return await ctx.send(_("You don't own both of these items."))
            if item["type"] == "Sword":
                stat1 = ("damage", item["damage"])
            elif item["type"] == "Shield":
                stat1 = ("armor", item["armor"])
            if item2["type"] == "Sword":
                stat2 = ("damage", item2["damage"])
            elif item2["type"] == "Shield":
                stat2 = ("armor", item2["armor"])
            if stat2[1] < stat1[1] - 5 or stat2[1] > stat1[1] + 5:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _(
                        "The second item's stat must be in the range of `{min_}` to `{max_}` to upgrade an item with the stat of `{stat}`."
                    ).format(min_=stat1[1] - 5, max_=stat1[1] + 5, stat=stat1[1])
                )
            if stat1[1] > 40:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("This item is already on the maximum upgrade level.")
                )
            await conn.execute(
                f'UPDATE allitems SET {stat1[0]}={stat1[0]}+1 WHERE "id"=$1;',
                firstitemid,
            )
            await conn.execute('DELETE FROM allitems WHERE "id"=$1;', seconditemid)
        await ctx.send(
            _(
                "The {stat} of your **{item}** is now **{newstat}**. The other item was destroyed."
            ).format(stat=stat1[0], item=item["name"], newstat=stat1[1] + 1)
        )

    @checks.has_char()
    @user_cooldown(3600)
    @commands.command(aliases=["upgrade"])
    @locale_doc
    async def upgradeweapon(self, ctx, itemid: int):
        _("""Upgrades an item's stat by 1.""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "id"=$1 AND "owner"=$2;',
                itemid,
                ctx.author.id,
            )
            if not item:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("You don't own an item with the ID `{itemid}`.").format(
                        itemid=itemid
                    )
                )
            if item["type"] == "Sword":
                stattoupgrade = "damage"
                pricetopay = int(item["damage"] * 250)
            elif item["type"] == "Shield":
                stattoupgrade = "armor"
                pricetopay = int(item["armor"] * 250)
            if int(item[stattoupgrade]) > 40:
                return await ctx.send(
                    _("Your weapon already reached the maximum upgrade level.")
                )
        if ctx.character_data["money"] < pricetopay:
            return await ctx.send(
                _(
                    "You are too poor to upgrade this item. The upgrade costs **${pricetopay}**, but you only have **${money}**."
                ).format(pricetopay=pricetopay, money=ctx.character_data["money"])
            )

        if not await ctx.confirm(
            _(
                "Are you sure you want to upgrade this item: {item}? It will cost **${pricetopay}**."
            ).format(item=item["name"], pricetopay=pricetopay)
        ):
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("Weapon upgrade cancelled."))
        if not await checks.has_money(self.bot, ctx.author.id, pricetopay):
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You're too poor."))
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
            _(
                "The {stat} of your **{item}** is now **{newstat}**. **${pricetopay}** has been taken off your balance."
            ).format(
                stat=stattoupgrade,
                item=item["name"],
                newstat=int(item[stattoupgrade]) + 1,
                pricetopay=pricetopay,
            )
        )

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def give(
        self, ctx, money: IntFromTo(0, 100_000_000), other: MemberWithCharacter
    ):
        _("""Gift money!""")
        if other == ctx.author:
            return await ctx.send(_("No cheating!"))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, other.id
            )
        await ctx.send(
            _("Successfully gave **${money}** to {other}.").format(
                money=money, other=other.mention
            )
        )
        await self.bot.log_transaction(
            ctx, from_=ctx.author, to=other, subject="money", data=money
        )

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def rename(self, ctx):
        _("""Renames your character.""")
        await ctx.send(
            _("What shall your character's name be? (Minimum 3 Characters, Maximum 20)")
        )

        def mycheck(amsg):
            return amsg.author == ctx.author

        try:
            name = await self.bot.wait_for("message", timeout=60, check=mycheck)
        except asyncio.TimeoutError:
            return await ctx.send(_("Timeout expired. Retry!"))
        name = name.content
        if len(name) > 2 and len(name) < 21:
            await self.bot.pool.execute(
                'UPDATE profile SET "name"=$1 WHERE "user"=$2;', name, ctx.author.id
            )
            await ctx.send(_("Character name updated."))
        elif len(name) < 3:
            await ctx.send(_("Character names must be at least 3 characters!"))
        elif len(name) > 20:
            await ctx.send(_("Character names mustn't exceed 20 characters!"))

    @checks.has_char()
    @commands.command(aliases=["rm", "del"])
    @locale_doc
    async def delete(self, ctx):
        _("""Deletes your character.""")
        if not await ctx.confirm(
            _(
                "Are you absolutely sure you want to delete your character? React in the next 30 seconds to confirm.\n**This cannot be undone!!**"
            )
        ):
            return await ctx.send(_("Cancelled deletion of your character."))
        async with self.bot.pool.acquire() as conn:
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
            _("Successfully deleted your character. Sorry to see you go :frowning:")
        )

    @commands.command(aliases=["color"])
    @locale_doc
    async def colour(self, ctx, colour: str):
        _("""Sets your profile text colour.""")
        if len(colour) != 7 or not colour.startswith("#"):
            return await ctx.send(_("Format for colour is `#RRGGBB`."))
        await self.bot.pool.execute(
            'UPDATE profile SET "colour"=$1 WHERE "user"=$2;', colour, ctx.author.id
        )
        await ctx.send(
            _("Successfully set your profile colour to `{colour}`.").format(
                colour=colour
            )
        )


def setup(bot):
    bot.add_cog(Profile(bot))
