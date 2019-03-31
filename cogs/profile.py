"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import functools
import asyncio

from discord.ext import commands
from utils import misc as rpgtools
from cogs.help import chunks
from io import BytesIO
from cogs.classes import genstats
from utils import checks
from cogs.shard_communication import user_on_cooldown as user_cooldown


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
    async def profile(self, ctx, *, person: discord.User = None):
        await ctx.trigger_typing()
        person = person or ctx.author
        targetid = person.id
        if not await checks.user_has_char(self.bot, targetid):
            return await ctx.send(f"**{person}** doesn't have a character.")
        async with self.bot.pool.acquire() as conn:
            ranks = []
            profile = await conn.fetchrow(
                'SELECT * FROM profile WHERE "user"=$1;', targetid
            )
            color = profile["colour"]
            sword = await conn.fetchrow(
                "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                targetid,
            )
            shield = await conn.fetchrow(
                "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                targetid,
            )
            ranks.append(
                (
                    await conn.fetchrow(
                        "SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.money DESC) AS position FROM profile) s WHERE s.user = $1 LIMIT 1;",
                        targetid,
                    )
                )[0]
            )
            ranks.append(
                (
                    await conn.fetchrow(
                        "SELECT position FROM (SELECT profile.*, ROW_NUMBER() OVER(ORDER BY profile.xp DESC) AS position FROM profile) s WHERE s.user = $1 LIMIT 1;",
                        targetid,
                    )
                )[0]
            )
            mission = await conn.fetchrow(
                'SELECT * FROM mission WHERE "name"=$1;', targetid
            )
            guild = await conn.fetchrow(
                'SELECT name FROM guild WHERE "id"=$1;', profile[12]
            )
            if not mission:
                mission = []
            missionend = []
            if mission != []:
                missionend = (
                    await conn.fetchrow("SELECT $1-clock_timestamp();", mission[2])
                )[0]
            background = profile["background"]
            if background == "0":
                background = "Profile.png"
            else:
                async with self.bot.session.get(background) as r:
                    background = BytesIO(await r.read())
                    background.seek(0)
            if str(profile[9]) != "0":
                marriage = (await rpgtools.lookup(self.bot, profile[9])).split("#")[0]
            else:
                marriage = "Not married"

            try:
                sword = [sword["name"], sword["damage"]]
            except KeyError:
                sword = ["None equipped", 0.00]
            try:
                shield = [shield["name"], shield["armor"]]
            except KeyError:
                shield = ["None equipped", 0.00]

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
            color,
            background,
            marriage,
            guild,
            extras,
        )
        output_buffer = await self.bot.loop.run_in_executor(None, thing)
        await ctx.send(file=discord.File(fp=output_buffer, filename="Profile.png"))

    @checks.has_char()
    @commands.command(aliases=["money", "e"], description="Shows your current balance.")
    async def economy(self, ctx):
        async with self.bot.pool.acquire() as conn:
            money = await conn.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', ctx.author.id
            )
        await ctx.send(f"You currently have **${money}**, {ctx.author.mention}!")

    @checks.has_char()
    @commands.command(description="Shows your current XP count.")
    async def xp(self, ctx):
        async with self.bot.pool.acquire() as conn:
            points = await conn.fetchval(
                'SELECT xp FROM profile WHERE "user"=$1;', ctx.author.id
            )
        await ctx.send(
            f"You currently have **{points} XP**, which means you are on Level **{rpgtools.xptolevel(points)}**. Missing to next level: **{rpgtools.xptonextlevel(points)}**"
        )

    async def invembed(self, ctx, ret):
        result = discord.Embed(
            title=f"{ctx.author.display_name}'s inventory includes", colour=discord.Colour.blurple()
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
        return result

    @checks.has_char()
    @commands.command(aliases=["inv", "i"], description="Shows your current inventory.")
    async def inventory(self, ctx):
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                "SELECT ai.*, i.equipped FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE p.user=$1 ORDER BY i.equipped DESC;",
                ctx.author.id,
            )
        if ret == []:
            await ctx.send("Your inventory is empty.")
        else:
            allitems = list(chunks(ret, 5))
            currentpage = 0
            maxpage = len(allitems) - 1
            result = await self.invembed(ctx, allitems[currentpage])
            result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
            msg = await ctx.send(embed=result)
            if maxpage == 0:
                return
            await msg.add_reaction("\U000023ee")
            await msg.add_reaction("\U000025c0")
            await msg.add_reaction("\U000025b6")
            await msg.add_reaction("\U000023ed")
            await msg.add_reaction("\U0001f522")

            def reactioncheck(reaction, user):
                return (
                    str(reaction.emoji)
                    in [
                        "\U000025c0",
                        "\U000025b6",
                        "\U000023ee",
                        "\U000023ed",
                        "\U0001f522",
                    ]
                    and reaction.message.id == msg.id
                    and user.id == ctx.author.id
                )

            def msgcheck(amsg):
                return amsg.channel == ctx.channel and not amsg.author.bot

            browsing = True
            while browsing:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=60.0, check=reactioncheck
                    )
                    if reaction.emoji == "\U000025c0":
                        if currentpage == 0:
                            pass
                        else:
                            currentpage -= 1
                            result = await self.invembed(allitems[currentpage])
                            result.set_footer(
                                text=f"Page {currentpage+1} of {maxpage+1}"
                            )
                            await msg.edit(embed=result)
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000025b6":
                        if currentpage == maxpage:
                            pass
                        else:
                            currentpage += 1
                            result = await self.invembed(allitems[currentpage])
                            result.set_footer(
                                text=f"Page {currentpage+1} of {maxpage+1}"
                            )
                            await msg.edit(embed=result)
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000023ed":
                        currentpage = maxpage
                        result = await self.invembed(allitems[currentpage])
                        result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
                        await msg.edit(embed=result)
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000023ee":
                        currentpage = 0
                        result = await self.invembed(allitems[currentpage])
                        result.set_footer(text=f"Page {currentpage+1} of {maxpage+1}")
                        await msg.edit(embed=result)
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U0001f522":
                        question = await ctx.send(
                            f"Enter a page number from `1` to `{maxpage+1}`"
                        )
                        num = await self.bot.wait_for(
                            "message", timeout=10, check=msgcheck
                        )
                        if num is not None:
                            try:
                                num2 = int(num.content)
                                if num2 >= 1 and num2 <= maxpage + 1:
                                    currentpage = num2 - 1
                                    result = await self.invembed(allitems[currentpage])
                                    result.set_footer(
                                        text=f"Page {currentpage+1} of {maxpage+1}"
                                    )
                                    await msg.edit(embed=result)
                                else:
                                    await ctx.send(
                                        f"Must be between `1` and `{maxpage+1}`.",
                                        delete_after=2,
                                    )
                                try:
                                    await num.delete()
                                except discord.Forbidden:
                                    pass
                            except ValueError:
                                await ctx.send("That is no number!", delete_after=2)
                        await question.delete()
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                except asyncio.TimeoutError:
                    browsing = False
                    try:
                        await msg.clear_reactions()
                    except discord.Forbidden:
                        pass
                    finally:
                        break

    @checks.has_char()
    @commands.command(aliases=["use"], description="Equips the item with the given ID.")
    async def equip(self, ctx, itemid: int):
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                "SELECT ai.id FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.owner=$1;",
                ctx.author.id,
            )
            if not ret:
                return await ctx.send("Your inventory is empty.")
            ids = [r[0] for r in ret]
            if itemid in ids:
                itemtype = await conn.fetchval(
                    'SELECT type FROM allitems WHERE "id"=$1;', itemid
                )
                olditem = await conn.fetchrow(
                    "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type=$2;",
                    ctx.author.id,
                    itemtype,
                )
                if olditem is not None:
                    await conn.execute(
                        'UPDATE inventory SET "equipped"=False WHERE "item"=$1;',
                        olditem[0],
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
            else:
                await ctx.send(f"You don't own an item with the ID `{itemid}`.")

    @checks.has_char()
    @user_cooldown(3600)
    @commands.command(description="Merges two items to a better item.")
    async def merge(self, ctx, firstitemid: int, seconditemid: int):
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
    @user_cooldown(60)
    @commands.command(aliases=["upgrade"], description="Upgrades an item's stat by 1.")
    async def upgradeweapon(self, ctx, itemid: int):
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT * FROM allitems WHERE "id"=$1 AND "owner"=$2;',
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID `{itemid}`.")
            if item[4] == "Sword":
                stattoupgrade = "damage"
                statid = 5
                pricetopay = int(item[5] * 250)
            elif item[4] == "Shield":
                stattoupgrade = "armor"
                statid = 6
                pricetopay = int(item[6] * 250)
            if int(item[statid]) > 40:
                return await ctx.send(
                    "Your weapon already reached the maximum upgrade level."
                )
            usermoney = await conn.fetchval(
                'SELECT money FROM profile WHERE "user"=$1;', ctx.author.id
            )
        if usermoney < pricetopay:
            return await ctx.send(
                f"You are too poor to upgrade this item. The upgrade costs **${pricetopay}**, but you only have **${usermoney}**."
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
        self.bot.reset_cooldown(ctx)
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
            f"The {stattoupgrade} of your **{item[2]}** is now **{int(item[statid])+1}**. **${pricetopay}** has been taken off your balance."
        )

    @checks.has_char()
    @commands.command(description="Gift money!")
    async def give(self, ctx, money: int, other: discord.Member):
        if money < 0 or money > 100_000_000:
            return await ctx.send("Don't scam!")
        if other == ctx.author:
            return await ctx.send("No cheating!")
        if not await checks.user_has_char(self.bot, other.id):
            return await ctx.send("That person doesn't have a character.")
        if not await checks.has_money(self.bot, ctx.author.id, money):
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
    @commands.command(description="Changes your character name")
    async def rename(self, ctx):
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
    @commands.command(aliases=["rm", "del"], description="Deletes your character.")
    async def delete(self, ctx):
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
            await conn.execute('DELETE FROM profile WHERE "user"=$1;', ctx.author.id)
        await ctx.send(
            "Successfully deleted your character. Sorry to see you go :frowning:"
        )

    @commands.command(
        aliases=["color"],
        description="Set your default text colour for the profile command.",
    )
    async def colour(self, ctx, colour: str):
        if len(colour) != 7 or not colour.startswith("#"):
            return await ctx.send("Format for colour is `#RRGGBB`.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "colour"=$1 WHERE "user"=$2;', colour, ctx.author.id
            )
        await ctx.send(f"Successfully set your profile colour to `{colour}`.")


def setup(bot):
    bot.add_cog(Profile(bot))
