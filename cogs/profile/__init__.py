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

from io import BytesIO

import discord

from discord.ext import commands
from discord.ext.commands.default import Author

from classes.converters import IntFromTo, MemberWithCharacter, User, UserWithCharacter
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
    async def create(self, ctx, *, name: str = None):
        _("""Creates a new character.""")
        if not name:
            await ctx.send(
                _(
                    """\
What shall your character's name be? (Minimum 3 Characters, Maximum 20)

**Please note that with the creation of a character, you agree to these rules:**
1) Only up to two characters per individual
2) No abusing or benefiting from bugs or exploits
3) Be friendly and kind to other players
4) Trading in-game items or currency for real money or items directly comparable to currency is forbidden
5) Giving or selling renamed items is forbidden

IdleRPG is a global bot, your characters are valid everywhere"""
                )
            )

            def mycheck(amsg):
                return amsg.author == ctx.author and amsg.channel == ctx.channel

            try:
                name = await self.bot.wait_for("message", timeout=60, check=mycheck)
            except asyncio.TimeoutError:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(_("Timeout expired. Please retry!"))
            name = name.content
        else:
            if not await ctx.confirm(
                _(
                    """\
**Please note that with the creation of a character, you agree to these rules:**
1) Only up to two characters per individual
2) No abusing or benefiting from bugs or exploits
3) Be friendly and kind to other players
4) Trading in-game items or currency for real money is forbidden
5) Giving or selling renamed items is forbidden

IdleRPG is a global bot, your characters are valid everywhere"""
                )
            ):
                return await ctx.send(_("Creation of your character cancelled."))
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
                hand="any",
                equipped=True,
            )
            await self.bot.create_item(
                name=_("Starter Shield"),
                value=0,
                type_="Shield",
                damage=0.0,
                armor=3.0,
                owner=ctx.author,
                hand="left",
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
            items = await self.bot.get_equipped_items_for(targetid)
            mission = await self.bot.get_adventure(targetid)
            guild = await conn.fetchval(
                'SELECT name FROM guild WHERE "id"=$1;', profile["guild"]
            )
            v1 = sum(i["damage"] for i in items)
            v2 = sum(i["armor"] for i in items)
            damage, armor = await self.bot.generate_stats(
                targetid, v1, v2, classes=profile["class"], race=profile["race"]
            )
            extras = (damage - v1, armor - v2)
            sworddmg = f"{v1}{' (+' + str(extras[0]) + ')' if extras[0] else ''}"
            shielddef = f"{v2}{' (+' + str(extras[1]) + ')' if extras[1] else ''}"

            right_hand = "None Equipped"
            left_hand = "None Equipped"

            any_count = sum(1 for i in items if i["hand"] == "any")
            if any_count == 1 and items[0]["hand"] == "any":
                items = [items[1], items[0]]

            for i in items:
                if i["hand"] == "both":
                    right_hand, left_hand = i["name"], i["name"]
                elif i["hand"] == "left":
                    left_hand = i["name"]
                elif i["hand"] == "right":
                    right_hand = i["name"]
                elif i["hand"] == "any":
                    if right_hand == "None Equipped":
                        right_hand = i["name"]
                    else:
                        left_hand = i["name"]

            url = f"{self.bot.config.okapi_url}/api/genprofile"
            async with self.bot.trusted_session.post(
                url,
                data={
                    "name": profile["name"],
                    "color": profile["colour"],
                    "image": profile["background"],
                    "race": profile["race"],
                    "classes": profile["class"],
                    "damage": sworddmg,
                    "defense": shielddef,
                    "swordName": right_hand,
                    "shieldName": left_hand,
                    "level": rpgtools.xptolevel(profile["xp"]),
                    "money": f"{profile['money']}",
                    "pvpWins": f"{profile['pvpwins']}",
                    "marriage": i
                    if (
                        i := await rpgtools.lookup(
                            self.bot, profile["marriage"], return_none=True
                        )
                    )
                    else _("Not Married"),
                    "guild": guild or _("No Guild"),
                    "god": profile["god"] or _("No God"),
                    "icons": [
                        self.bot.get_class_line(c).lower() for c in profile["class"]
                    ],
                    "adventure": f"Adventure {mission[0]}\n{mission[1] if not mission[2] else _('Finished')}"
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

        items = await self.bot.get_equipped_items_for(target)
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

        right_hand = None
        left_hand = None

        any_count = sum(1 for i in items if i["hand"] == "any")
        if any_count == 1 and items[0]["hand"] == "any":
            items = [items[1], items[0]]

        for i in items:
            if i["hand"] == "both":
                right_hand, left_hand = i, i
            elif i["hand"] == "left":
                left_hand = i
            elif i["hand"] == "right":
                right_hand = i
            elif i["hand"] == "any":
                if right_hand is None:
                    right_hand = i
                else:
                    left_hand = i

        right_hand = (
            f"{right_hand['name']} - {right_hand['damage'] + right_hand['armor']}"
            if right_hand
            else _("None Equipped")
        )
        left_hand = (
            f"{left_hand['name']} - {left_hand['damage'] + left_hand['armor']}"
            if left_hand
            else _("None Equipped")
        )
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
**Race**: `{race}`
**PvP Wins**: `{pvp}`
**Guild**: `{guild}`"""
            ).format(
                money=p_data["money"],
                level=level,
                class_="/".join(p_data["class"]),
                race=p_data["race"],
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
            value=_("Right Hand: {right_hand}\nLeft Hand: {left_hand}").format(
                right_hand=right_hand, left_hand=left_hand
            ),
        )
        if mission:
            em.add_field(name=_("Mission"), value=f"{mission[0]} - {timeleft}")
        await ctx.send(embed=em)

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def luck(self, ctx):
        _("""Shows your luck factor ranging from 0 to 2.""")
        await ctx.send(
            _(
                "Your current luck multiplier is `{luck}x` (≈{percent}% more than usual (usual=1))."
            ).format(
                luck=ctx.character_data["luck"],
                percent=(ctx.character_data["luck"] - 1) * 100,
            )
        )

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
    async def xp(self, ctx, user: UserWithCharacter = Author):
        _("""Shows current XP and level of a player.""")
        if user.id == ctx.author.id:
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
        else:
            points = ctx.user_data["xp"]
            await ctx.send(
                _(
                    "{user} has **{points} XP** and is on Level **{level}**. Missing to next level: **{missing}**"
                ).format(
                    user=user,
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
            if weapon["equipped"]:
                eq = _("(**Equipped**)")
            else:
                eq = ""
            statstr = (
                _("Damage: `{damage}`").format(damage=weapon["damage"])
                if weapon["type"] != "Shield"
                else _("Armor: `{armor}`").format(armor=weapon["armor"])
            )
            signature = (
                _("\nSignature: *{signature}*").format(signature=y)
                if (y := weapon["signature"])
                else ""
            )
            result.add_field(
                name=f"{weapon['name']} {eq}",
                value=_(
                    "ID: `{id}`, Type: `{type_}` (uses {hand} hand(s)) with {statstr}. Value is **${value}**{signature}"
                ).format(
                    id=weapon["id"],
                    type_=weapon["type"],
                    hand=weapon["hand"],
                    statstr=statstr,
                    value=weapon["value"],
                    signature=signature,
                ),
                inline=False,
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
    async def inventory(
        self, ctx, lowest: IntFromTo(0, 100) = 0, highest: IntFromTo(0, 100) = 100
    ):
        _("""Shows your current inventory.""")
        if highest < lowest:
            return await ctx.send(
                _("Make sure that the `highest` value is greater than `lowest`.")
            )
        ret = await self.bot.pool.fetch(
            'SELECT ai.*, i.equipped FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE p."user"=$1 AND ((ai."damage"+ai."armor" BETWEEN $2 AND $3) OR i."equipped") ORDER BY i."equipped" DESC, ai."damage"+ai."armor" DESC;',
            ctx.author.id,
            lowest,
            highest,
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

    def lootembed(self, ctx, ret, currentpage, maxpage):
        result = discord.Embed(
            title=_("{user} has the following loot items.").format(user=ctx.disp),
            colour=discord.Colour.blurple(),
        )
        for item in ret:
            result.add_field(
                name=item["name"],
                value=_("ID: `{id}` Value is **{value}**").format(
                    id=item["id"], value=item["value"]
                ),
                inline=False,
            )
        result.set_footer(
            text=_("Page {page} of {maxpages}").format(
                page=currentpage + 1, maxpages=maxpage + 1
            )
        )
        return result

    @checks.has_char()
    @commands.command(aliases=["loot"])
    @locale_doc
    async def items(self, ctx):
        _("""Shows your adventure loot that can be exchanged or sacrificed""")
        ret = await self.bot.pool.fetch(
            'SELECT * FROM loot WHERE "user"=$1;', ctx.author.id
        )
        if not ret:
            return await ctx.send(_("You do not have any loot at this moment."))
        allitems = list(chunks(ret, 7))
        maxpage = len(allitems) - 1
        embeds = [
            self.lootembed(ctx, chunk, idx, maxpage)
            for idx, chunk in enumerate(allitems)
        ]
        await self.bot.paginator.Paginator(extras=embeds).paginate(ctx)

    @checks.has_char()
    @user_cooldown(600)
    @commands.command(aliases=["ex"])
    @locale_doc
    async def exchange(self, ctx, *loot_ids: int):
        _("""Exchange one or more loot items for money or xp.""")
        if (none_given := (len(loot_ids) == 0)) :
            async with self.bot.pool.acquire() as conn:
                value, count = await conn.fetchval(
                    'SELECT (SUM("value"), COUNT(*)) FROM loot WHERE "user"=$1',
                    ctx.author.id,
                )
                if count == 0:
                    await self.bot.reset_cooldown(ctx)
                    return await ctx.send(_("You don't have any loot."))
        else:
            async with self.bot.pool.acquire() as conn:
                value, count = await conn.fetchval(
                    'SELECT (SUM("value"), COUNT("value")) FROM loot WHERE "id"=ANY($1) AND "user"=$2;',
                    loot_ids,
                    ctx.author.id,
                )

                if not count:
                    return await ctx.send(
                        _(
                            "You don't own any loot items with the IDs: {itemids}"
                        ).format(
                            itemids=", ".join([str(loot_id) for loot_id in loot_ids])
                        )
                    )
        reward = await self.bot.paginator.Choose(
            title=_("Select a reward for the {amount} items".format(amount=count)),
            footer=_("Do you want favor? {prefix}sacrifice instead").format(
                prefix=ctx.prefix
            ),
            return_index=True,
            entries=[f"**${value}**", _("**{value} XP**").format(value=value // 4)],
        ).paginate(ctx)
        reward = ["money", "xp"][reward]
        if reward == "xp":
            old_level = int(rpgtools.xptolevel(ctx.character_data["xp"]))
            value = value // 4

        async with self.bot.pool.acquire() as conn:
            if len(loot_ids) == 0:
                await conn.execute('DELETE FROM loot WHERE "user"=$1;', ctx.author.id)
            else:
                await conn.execute(
                    'DELETE FROM loot WHERE "id"=ANY($1) AND "user"=$2;',
                    loot_ids,
                    ctx.author.id,
                )
            await conn.execute(
                f'UPDATE profile SET "{reward}"="{reward}"+$1 WHERE "user"=$2;',
                value,
                ctx.author.id,
            )
        if none_given:
            text = _(
                "You received **{reward}** when exchanging all of your loot."
            ).format(reward=f"${value}" if reward == "money" else f"{value} XP")
        else:
            text = _(
                "You received **{reward}** when exchanging loot item(s) `{loot_ids}`. "
            ).format(
                reward=f"${value}" if reward == "money" else f"{value} XP",
                loot_ids=", ".join([str(lootid) for lootid in loot_ids]),
            )
        additional = _("Skipped `{amount}` because they did not belong to you.").format(
            amount=len(loot_ids) - count
        )
        # if len(loot_ids) > count else ""

        await ctx.send(text + (additional if len(loot_ids) > count else ""))

        if reward == "xp":
            new_level = int(rpgtools.xptolevel(ctx.character_data["xp"] + value))
            if old_level != new_level:
                await self.bot.process_levelup(ctx, new_level)

        await self.bot.reset_cooldown(ctx)

    @user_cooldown(180)
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
            olditems = await conn.fetch(
                "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1;",
                ctx.author.id,
            )
            if olditems:
                num_any = sum(1 for i in olditems if i["hand"] == "any")
                if len(olditems) == 1 and olditems[0]["hand"] == "both":
                    await conn.execute(
                        'UPDATE inventory SET "equipped"=False WHERE "item"=$1;',
                        olditems[0]["id"],
                    )
                    put_off = [olditems[0]["id"]]
                elif item["hand"] == "both":
                    all_ids = [i["id"] for i in olditems]
                    await conn.execute(
                        'UPDATE inventory SET "equipped"=False WHERE "item"=ANY($1);',
                        all_ids,
                    )
                    put_off = all_ids
                else:
                    if (
                        item["hand"] == "left" or item["hand"] == "right"
                    ) and num_any < 2:
                        item_to_remove = [
                            i for i in olditems if i["hand"] == item["hand"]
                        ]
                        if not item_to_remove and len(olditems) == 2:
                            item_to_remove = [i for i in olditems if i["hand"] == "any"]
                        item_to_remove = item_to_remove[0]["id"]
                        await conn.execute(
                            'UPDATE inventory SET "equipped"=False WHERE "item"=$1;',
                            item_to_remove,
                        )
                        put_off = [item_to_remove]
                    elif item["hand"] == "any" and len(olditems) < 2:
                        pass  # just so last won't trigger
                    else:
                        item_to_remove = await self.bot.paginator.Choose(
                            title=_("Select an item to unequip"),
                            footer=_("Hit the button with the item you wish to remove"),
                            return_index=True,
                            entries=[
                                f"{i['name']}, {i['type']}, {i['damage'] + i['armor']}"
                                for i in olditems
                            ],
                        ).paginate(ctx)
                        item_to_remove = olditems[item_to_remove]["id"]
                        await conn.execute(
                            'UPDATE inventory SET "equipped"=False WHERE "item"=$1;',
                            item_to_remove,
                        )
                        put_off = [item_to_remove]
            await conn.execute(
                'UPDATE inventory SET "equipped"=True WHERE "item"=$1;', itemid
            )
        await self.bot.reset_cooldown(ctx)
        if olditems:
            await ctx.send(
                _(
                    "Successfully equipped item `{itemid}` and put off item(s) {olditems}."
                ).format(
                    olditems=", ".join(f"`{i}`" for i in put_off), itemid=item["id"]
                )
            )
        else:
            await ctx.send(
                _("Successfully equipped item `{itemid}`.").format(itemid=itemid)
            )

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def unequip(self, ctx, itemid: int):
        _("""Unequip one of your equipped items""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM inventory i JOIN allitems ai ON (i."item"=ai."id") WHERE ai."owner"=$1 and ai."id"=$2;',
                ctx.author.id,
                itemid,
            )
            if not item:
                return await ctx.send(
                    _("You don't own an item with the ID `{itemid}`.").format(
                        itemid=itemid
                    )
                )
            if not item["equipped"]:
                return await ctx.send(_("You don't have this item equipped."))
            await conn.execute(
                'UPDATE inventory SET "equipped"=False WHERE "item"=$1;', itemid
            )
        await ctx.send(
            _("Successfully unequipped item `{itemid}`.").format(itemid=itemid)
        )

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
            if item["type"] != item2["type"]:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _(
                        "The items are of unequal type. You may only merge a sword with a sword or a shield with a shield."
                    )
                )
            stat = "damage" if item["type"] != "Shield" else "armor"
            min_ = item[stat] - 5
            main = item[stat]
            main2 = item2[stat]
            max_ = item[stat] + 5
            if main > 40:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("This item is already on the maximum upgrade level.")
                )
            if not min_ <= main2 <= max_:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _(
                        "The second item's stat must be in the range of `{min_}` to `{max_}` to upgrade an item with the stat of `{stat}`."
                    ).format(min_=min_, max_=max_, stat=main)
                )
            await conn.execute(
                f'UPDATE allitems SET "{stat}"="{stat}"+1 WHERE "id"=$1;', firstitemid
            )
            await conn.execute('DELETE FROM allitems WHERE "id"=$1;', seconditemid)
        await ctx.send(
            _(
                "The {stat} of your **{item}** is now **{newstat}**. The other item was destroyed."
            ).format(stat=stat, item=item["name"], newstat=main + 1)
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
            if item["type"] != "Shield":
                stattoupgrade = "damage"
                pricetopay = int(item["damage"] * 250)
            elif item["type"] == "Shield":
                stattoupgrade = "armor"
                pricetopay = int(item["armor"] * 250)
            if int(item[stattoupgrade]) > 40:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("Your weapon already reached the maximum upgrade level.")
                )

        if not await ctx.confirm(
            _(
                "Are you sure you want to upgrade this item: {item}? It will cost **${pricetopay}**."
            ).format(item=item["name"], pricetopay=pricetopay)
        ):
            return await ctx.send(_("Weapon upgrade cancelled."))
        if not await checks.has_money(self.bot, ctx.author.id, pricetopay):
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(
                _(
                    "You are too poor to upgrade this item. The upgrade costs **${pricetopay}**, but you only have **${money}**."
                ).format(pricetopay=pricetopay, money=ctx.character_data["money"])
            )
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
            authormoney = await conn.fetchval(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2 RETURNING money;',
                money,
                ctx.author.id,
            )
            othermoney = await conn.fetchval(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2 RETURNING money;',
                money,
                other.id,
            )
        await ctx.send(
            _(
                "Success!\n{other} now has **${othermoney}**, you now have **${authormoney}**."
            ).format(
                other=other.mention, othermoney=othermoney, authormoney=authormoney
            )
        )
        await self.bot.log_transaction(
            ctx, from_=ctx.author, to=other, subject="money", data=money
        )

    @checks.has_char()
    @commands.command()
    @locale_doc
    async def rename(self, ctx, *, name: str = None):
        _("""Renames your character.""")
        if not name:
            await ctx.send(
                _(
                    "What shall your character's name be? (Minimum 3 Characters, Maximum 20)"
                )
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
                "Are you absolutely sure you want to delete your character? React in the next 30 seconds to confirm.\n**This cannot be undone.**"
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
                await conn.execute('UPDATE city SET "owner"=1 WHERE "owner"=$1;', g)
            await conn.execute(
                'UPDATE profile SET "marriage"=$1 WHERE "marriage"=$2;',
                0,
                ctx.author.id,
            )
            await conn.execute(
                'DELETE FROM children WHERE "mother"=$1 OR "father"=$1;', ctx.author.id
            )
            await conn.execute('DELETE FROM profile WHERE "user"=$1;', ctx.author.id)
        await self.bot.delete_adventure(ctx.author)
        await ctx.send(
            _("Successfully deleted your character. Sorry to see you go :frowning:")
        )

    @commands.command(aliases=["color"])
    @locale_doc
    async def colour(self, ctx, colour: str):
        _(
            """Sets your profile text colour. The format may be #RRGGBB or a HTML-valid string like "cyan"."""
        )
        if len(colour) > 15:
            return await ctx.send(
                _("Format for colour is `#RRGGBB` or a colour code like `cyan`.")
            )
        await self.bot.pool.execute(
            'UPDATE profile SET "colour"=$1 WHERE "user"=$2;', colour, ctx.author.id
        )
        await ctx.send(
            _(
                "Successfully set your profile colour to `{colour}`. Hint: If you used a hex colour code, you must include the `#`."
            ).format(colour=colour)
        )


def setup(bot):
    bot.add_cog(Profile(bot))
