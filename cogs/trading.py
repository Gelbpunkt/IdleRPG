"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import random

import discord
from discord.ext import commands

from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import misc as rpgtools
from utils.checks import has_char, has_money


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.markdown_escaper = commands.clean_content(escape_markdown=True)

    @has_char()
    @commands.command(
        description="Sells the item with the given ID for the given price."
    )
    async def sell(self, ctx, itemid: int, price: int):
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not ret:
                return await ctx.send(f"You don't own an item with the ID: {itemid}")
            if int(ret[8]) == 0 and int(ret[9]) <= 3:
                return await ctx.send(
                    "Your item is either equal to a Starter Item or worse. Noone would buy it."
                )
            elif int(ret[9]) == 0 and int(ret[8]) <= 3:
                return await ctx.send(
                    "Your item is either equal to a Starter Item or worse. Noone would buy it."
                )
            elif price > ret[6] * 50:
                return await ctx.send(
                    f"Your price is too high. Try adjusting it to be up to `{ret[6]*50}`."
                )
            elif price < 1:
                return await ctx.send("You can't sell it for free or a negative price.")
            await conn.execute(
                "DELETE FROM inventory i USING allitems ai WHERE i.item=ai.id AND ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO market (item, price) VALUES ($1, $2);", itemid, price
            )
        await ctx.send(
            f"Successfully added your item to the shop! Use `{ctx.prefix}shop` to view it in the market!"
        )

    @has_char()
    @commands.command(aliases=["b"], description="Buys an item with the given ID.")
    async def buy(self, ctx, itemid: int):
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE ai.id=$1;",
                itemid,
            )
            if not item:
                return await ctx.send(
                    f"There is no item in the shop with the ID: {itemid}"
                )
            if not await has_money(self.bot, ctx.author.id, item[2]):
                return await ctx.send("You're too poor to buy this item.")
            deleted = await conn.fetchrow(
                "DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=$1 AND ai.owner=$2 RETURNING *;",
                itemid,
                item[4],
            )
            await conn.execute(
                "UPDATE allitems SET owner=$1 WHERE id=$2;", ctx.author.id, deleted[3]
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                deleted[2],
                deleted[4],
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                deleted[2],
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO inventory (item, equipped) VALUES ($1, $2);",
                deleted[3],
                False,
            )
        await ctx.send(
            f"Successfully bought item `{deleted[3]}`. Use `{ctx.prefix}inventory` to view your updated inventory."
        )
        seller = await self.bot.get_user_global(deleted[4])
        if seller:
            await seller.send(
                f"**{ctx.author}** bought your **{deleted['name']}** for **${deleted['price']}** from the market."
            )

    @has_char()
    @commands.command(description="Takes an item off the shop.")
    async def remove(self, ctx, itemid: int):
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    f"You don't have an item of yours in the shop with the ID `{itemid}`."
                )
            await conn.execute(
                "DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO inventory (item, equipped) VALUES ($1, $2);", itemid, False
            )
        await ctx.send(
            f"Successfully removed item `{itemid}` from the shop and put it in your inventory."
        )

    @commands.command(
        aliases=["market", "m"],
        description="Show the market with all items and prices.",
    )
    async def shop(
        self,
        ctx,
        itemtype: str = "All",
        minstat: float = 0.00,
        highestprice: int = 10000,
    ):
        itemtype = itemtype.title()
        if itemtype not in ["All", "Sword", "Shield"]:
            return await ctx.send(
                "Use either `all`, `Sword` or `Shield` as a type to filter for."
            )
        if highestprice < 0:
            return await ctx.send("Price must be minimum 0.")
        async with self.bot.pool.acquire() as conn:
            if itemtype == "All":
                ret = await conn.fetch(
                    'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE m."price"<=$1 AND (ai."damage">=$2 OR ai."armor">=$3);',
                    highestprice,
                    minstat,
                    minstat,
                )
            elif itemtype == "Sword":
                ret = await conn.fetch(
                    'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=$1 AND ai."damage">=$2 AND m."price"<=$3;',
                    itemtype,
                    minstat,
                    highestprice,
                )
            elif itemtype == "Shield":
                ret = await conn.fetch(
                    'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=$1 AND ai."armor">=$2 AND m."price"<=$3;',
                    itemtype,
                    minstat,
                    highestprice,
                )
        if ret == []:
            await ctx.send("The shop is currently empty.")

        elif len(ret) == 1:
            charname = await rpgtools.lookup(self.bot, ret[0][1])
            clean_charname = await self.markdown_escaper.convert(ctx, charname)
            msg = await ctx.send(
                f"Item **1** of **1**\n\nSeller: `{clean_charname}`\nName: `{ret[0][2]}`\nValue: **${ret[0][3]}**\nType: `{ret[0][4]}`\nDamage: `{ret[0][5]}`\nArmor: `{ret[0][6]}`\nPrice: **${ret[0][9]}**\n\nUse: `{ctx.prefix}buy {ret[0][0]}` to buy this item."
            )
        else:
            maxpages = len(ret)
            currentpage = 1
            charname = await rpgtools.lookup(self.bot, ret[currentpage - 1][1])
            clean_charname = await self.markdown_escaper.convert(ctx, charname)
            msg = await ctx.send(
                f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
            )
            await msg.add_reaction("\U000023ee")
            await msg.add_reaction("\U000025c0")
            await msg.add_reaction("\U000025b6")
            await msg.add_reaction("\U000023ed")
            await msg.add_reaction("\U0001f522")
            shopactive = True

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
                    and user != self.bot.user
                    and user == ctx.author
                )

            def msgcheck(amsg):
                return amsg.channel == ctx.channel and not amsg.author.bot

            while shopactive:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=60.0, check=reactioncheck
                    )
                    if reaction.emoji == "\U000025c0":
                        if currentpage == 1:
                            pass
                        else:
                            currentpage -= 1
                            charname = await rpgtools.lookup(
                                self.bot, ret[currentpage - 1][1]
                            )
                            clean_charname = await self.markdown_escaper.convert(
                                ctx, charname
                            )
                            await msg.edit(
                                content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
                            )
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000025b6":
                        if currentpage == maxpages:
                            pass
                        else:
                            currentpage += 1
                            charname = await rpgtools.lookup(
                                self.bot, ret[currentpage - 1][1]
                            )
                            clean_charname = await self.markdown_escaper.convert(
                                ctx, charname
                            )
                            await msg.edit(
                                content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
                            )
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000023ee":
                        currentpage = 1
                        charname = await rpgtools.lookup(
                            self.bot, ret[currentpage - 1][1]
                        )
                        clean_charname = await self.markdown_escaper.convert(
                            ctx, charname
                        )
                        await msg.edit(
                            content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
                        )
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U000023ed":
                        currentpage = maxpages
                        charname = await rpgtools.lookup(
                            self.bot, ret[currentpage - 1][1]
                        )
                        clean_charname = await self.markdown_escaper.convert(
                            ctx, charname
                        )
                        statstr = (
                            f"Damage: `{ret[currentpage-1][5]}`"
                            if ret[currentpage - 1][4] == "Sword"
                            else f"Armor: `{ret[currentpage-1][6]}`"
                        )
                        await msg.edit(
                            content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\n{statstr}\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
                        )
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                    elif reaction.emoji == "\U0001f522":
                        question = await ctx.send(
                            f"Enter a page number from `1` to `{maxpages}`"
                        )
                        num = await self.bot.wait_for(
                            "message", timeout=10, check=msgcheck
                        )
                        if num is None:
                            await question.delete()
                        else:
                            try:
                                num2 = int(num.content)
                                if num2 >= 1 and num2 <= maxpages:
                                    currentpage = num2
                                    charname = await rpgtools.lookup(
                                        self.bot, ret[currentpage - 1][1]
                                    )
                                    clean_charname = await self.markdown_escaper.convert(
                                        ctx, charname
                                    )
                                    await msg.edit(
                                        content=f"Item **{currentpage}** of **{maxpages}**\n\nSeller: `{clean_charname}`\nName: `{ret[currentpage-1][2]}`\nValue: **${ret[currentpage-1][3]}**\nType: `{ret[currentpage-1][4]}`\nDamage: `{ret[currentpage-1][5]}`\nArmor: `{ret[currentpage-1][6]}`\nPrice: **${ret[currentpage-1][9]}**\n\nUse: `{ctx.prefix}buy {ret[currentpage-1][0]}` to buy this item."
                                    )
                                else:
                                    await ctx.send(
                                        f"Must be between `1` and `{maxpages}`.",
                                        delete_after=2,
                                    )
                                try:
                                    await num.delete()
                                except discord.Forbidden:
                                    pass
                            except ValueError:
                                await ctx.send("That is no number!", delete_after=2)
                                try:
                                    await num.delete()
                                except discord.Forbidden:
                                    pass
                        await question.delete()
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass
                except asyncio.TimeoutError:
                    shopactive = False
                    try:
                        await msg.clear_reactions()
                    except discord.Forbidden:
                        pass
                    finally:
                        break

    @has_char()
    @user_cooldown(180)
    @commands.command(description="Offer an item to a specific user.")
    async def offer(self, ctx, itemid: int, price: int, user: discord.Member):
        if price < 0 or price > 100_000_000:
            return await ctx.send("Don't scam!")
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
        if not ret:
            return await ctx.send(f"You don't have an item with the ID `{itemid}`.")
        if ret[2]:

            def check(m):
                return m.content.lower() == "confirm" and m.author == ctx.author

            await ctx.send(
                "Are you sure you want to sell your equipped item? Type `confirm` to sell it"
            )
            try:
                await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("Item selling cancelled.")
        await ctx.send(
            f"{user.mention}, {ctx.author.mention} offered you an item! Write `buy @{str(ctx.author)}` to buy it! The price is **${price}**. You have **2 Minutes** to accept the trade or the offer will be canceled."
        )

        def msgcheck(amsg):
            return (
                amsg.content.lower() == f"buy <@{ctx.author.id}>"
                or amsg.content.lower() == f"buy <@!{ctx.author.id}>"
            ) and amsg.author == user

        try:
            await self.bot.wait_for("message", timeout=120, check=msgcheck)
        except asyncio.TimeoutError:
            return await ctx.send(
                f"They didn't want to buy your item, {ctx.author.mention}."
            )
        if not await has_money(self.bot, user.id, price):
            return await ctx.send(f"{user.mention}, you're too poor to buy this item!")
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not ret:
                return await ctx.send(
                    f"The owner sold the item with the ID `{itemid}` in the meantime."
                )
            await conn.execute(
                "UPDATE allitems SET owner=$1 WHERE id=$2;", user.id, itemid
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                price,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;', price, user.id
            )
            await conn.execute(
                'UPDATE inventory SET "equipped"=$1 WHERE "item"=$2;', False, itemid
            )
        await ctx.send(
            f"Successfully bought item `{itemid}`. Use `{ctx.prefix}inventory` to view your updated inventory."
        )

    @has_char()
    @commands.command(aliases=["merch"], description="Sells an item for its value.")
    async def merchant(self, ctx, itemid: int):
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID: {itemid}")
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                item[6],
                ctx.author.id,
            )
            await conn.execute('DELETE FROM allitems WHERE "id"=$1;', itemid)
        await ctx.send(f"You received **${item[6]}** when selling item `{itemid}`.")

    @has_char()
    @user_cooldown(1800)
    @commands.command()
    async def merchall(self, ctx):
        """Sells all your non-equipped items for their value."""
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetchrow(
                "SELECT sum(value), count(value) FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.owner=$1 AND i.equipped IS FALSE;",
                ctx.author.id,
            )
            if ret[1] == 0:
                return await ctx.send("Nothing to merch.")
            await conn.execute(
                "DELETE FROM allitems ai USING inventory i WHERE ai.id=i.item AND ai.owner=$1 AND i.equipped IS FALSE;",
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                ret[0],
                ctx.author.id,
            )
        await ctx.send(f"Merched **{ret[1]}** items for **${ret[0]}**.")

    @commands.command(description="Views your pending shop items.")
    async def pending(self, ctx):
        async with self.bot.pool.acquire() as conn:
            ret = await conn.fetch(
                'SELECT * FROM allitems ai JOIN market m ON (m.item=ai.id) WHERE ai."owner"=$1;',
                ctx.author.id,
            )
        if ret == []:
            return await ctx.send("You don't have any pending shop offers.")
        p = "**Your current shop offers**\n"
        for row in ret:
            p += f"A **{row[2]}** (ID: `{row[0]}`) with damage `{row[5]}` and armor `{row[6]}`. Value is **${row[3]}**, market price is **${row[9]}**.\n"
        await ctx.send(p)

    @has_char()
    @user_cooldown(3600)
    @commands.command(description="Buy items at the trader.")
    async def trader(self, ctx):
        # [type, damage, armor, value (0), name, price]
        offers = []
        for i in range(5):
            name = random.choice(
                ["Normal ", "Ugly ", "Useless ", "Premade ", "Handsmith "]
            )
            type = random.choice(["Sword", "Shield"])
            name = (
                name + random.choice(["Blade", "Stich", "Sword"])
                if type == "Sword"
                else name
            )
            name = (
                name + random.choice(["Defender", "Aegis", "Buckler"])
                if type == "Shield"
                else name
            )
            damage = random.randint(1, 15) if type == "Sword" else 0
            armor = random.randint(1, 15) if type == "Shield" else 0
            price = armor * 50 + damage * 50
            offers.append([type, damage, armor, 0, name, price])
        nl = "\n"
        await ctx.send(
            f"""
**The trader offers once per hour:**
{nl.join([str(offers.index(w)+1)+") Type: `"+w[0]+"` Damage: `"+str(w[1])+".00` Armor: `"+str(w[2])+".00` Name: `"+w[4]+"` Price: **$"+str(w[5])+"**" for w in offers])}

Type `trader buy offerid` in the next 30 seconds to buy something
"""
        )

        def check(msg):
            return (
                msg.content.lower().startswith("trader buy")
                and msg.author == ctx.author
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return

        try:
            offerid = int(msg.content.split()[-1])
        except ValueError:
            return await ctx.send("Unknown offer")
        if offerid < 1 or offerid > 5:
            return await ctx.send("Unknown offer")
        offerid = offerid - 1
        item = offers[offerid]
        if not await has_money(self.bot, ctx.author.id, item[5]):
            return await ctx.send("You are too poor to buy this item.")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                item[5],
                ctx.author.id,
            )
            itemid = await conn.fetchval(
                'INSERT INTO allitems ("owner", "name", "value", "type", "damage", "armor") VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;',
                ctx.author.id,
                item[4],
                0,
                item[0],
                item[1],
                item[2],
            )
            await conn.execute(
                'INSERT INTO inventory ("item", "equipped") VALUES ($1, $2);',
                itemid,
                False,
            )
        await ctx.send(
            f"Successfully bought offer **{offerid+1}**. Use `{ctx.prefix}inventory` to view your updated inventory."
        )


def setup(bot):
    bot.add_cog(Trading(bot))
