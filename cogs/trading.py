"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import random

import discord
from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_money


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.markdown_escaper = commands.clean_content(escape_markdown=True)

    @has_char()
    @commands.command()
    async def sell(self, ctx, itemid: int, price: IntGreaterThan(-1)):
        """Puts an item into the player store."""
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID: {itemid}")
            if item["damage"] < 4 and item["armor"] < 4:
                return await ctx.send(
                    "Your item is either equal to a Starter Item or worse. Noone would buy it."
                )
            elif price > item["value"] * 1000:
                return await ctx.send(
                    f"Your price is too high. Try adjusting it to be up to `{item[6] * 50}`."
                )
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
    @commands.command(aliases=["b"])
    async def buy(self, ctx, itemid: int):
        """Buys an item from the global market."""
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE ai.id=$1;",
                itemid,
            )
            if not item:
                return await ctx.send(
                    f"There is no item in the shop with the ID: {itemid}"
                )
            if ctx.character_data["money"] < item["price"]:
                return await ctx.send("You're too poor to buy this item.")
            await conn.execute(
                "DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=$1 RETURNING *;",
                itemid,
            )
            await conn.execute(
                "UPDATE allitems SET owner=$1 WHERE id=$2;", ctx.author.id, item["id"]
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                item["price"],
                item["owner"],
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                item["price"],
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO inventory (item, equipped) VALUES ($1, $2);",
                item["id"],
                False,
            )
        await ctx.send(
            f"Successfully bought item `{item['id']}`. Use `{ctx.prefix}inventory` to view your updated inventory."
        )
        seller = await self.bot.get_user_global(item["owner"])
        if seller:
            await seller.send(
                f"**{ctx.author}** bought your **{item['name']}** for **${item['price']}** from the market."
            )

    @has_char()
    @commands.command()
    async def remove(self, ctx, itemid: int):
        """Takes an item off the shop."""
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

    @commands.command(aliases=["market", "m"])
    async def shop(
        self,
        ctx,
        itemtype: str.title = "All",
        minstat: float = 0.00,
        highestprice: IntGreaterThan(-1) = 1_000_000,
    ):
        if itemtype not in ["All", "Sword", "Shield"]:
            return await ctx.send(
                "Use either `All`, `Sword` or `Shield` as a type to filter for."
            )
        if itemtype == "All":
            items = await self.bot.pool.fetch(
                'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE m."price"<=$1 AND (ai."damage">=$2 OR ai."armor">=$3);',
                highestprice,
                minstat,
                minstat,
            )
        elif itemtype == "Sword":
            items = await self.bot.pool.fetch(
                'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=$1 AND ai."damage">=$2 AND m."price"<=$3;',
                itemtype,
                minstat,
                highestprice,
            )
        elif itemtype == "Shield":
            items = await self.bot.pool.fetch(
                'SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE ai."type"=$1 AND ai."armor">=$2 AND m."price"<=$3;',
                itemtype,
                minstat,
                highestprice,
            )
        if not items:
            await ctx.send("No results.")

        items = [
            discord.Embed(
                title="IdleRPG Shop",
                description=f"Use `{ctx.prefix}buy {item['id']}` to buy this.",
                colour=discord.Colour.blurple(),
            )
            .add_field(name="Name", value=item["name"])
            .add_field(name="Type", value=item["type"])
            .add_field(name="Damage", value=item["damage"])
            .add_field(name="Armor", value=item["armor"])
            .add_field(name="Value", value=f"${item['value']}")
            .add_field(name="Price", value=f"${item['price']}")
            .set_footer(text=f"Item {idx + 1} of {len(items)}")
            for idx, item in enumerate(items)
        ]
        await self.bot.paginator.Paginator(extras=items).paginate(ctx)

    @has_char()
    @user_cooldown(180)
    @commands.command()
    async def offer(
        self, ctx, itemid: int, price: IntFromTo(0, 100_000_000), user: discord.Member
    ):
        """Offer an item to a specific user."""
        item = await self.bot.pool.fetchrow(
            "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
            itemid,
            ctx.author.id,
        )
        if not item:
            return await ctx.send(f"You don't have an item with the ID `{itemid}`.")

        if item["equipped"]:
            if not await ctx.confirm(
                f"Are you sure you want to sell your equipped {item['name']}?"
            ):
                await ctx.send("Item selling cancelled.")

        if not await ctx.confirm(
            f"{user.mention}, {ctx.author.mention} offered you an item! React to buy it! The price is **${price}**. You have **2 Minutes** to accept the trade or the offer will be canceled.",
            user=user,
            timeout=120,
        ):
            return await ctx.send("They didn't want it.")

        if not await has_money(self.bot, user.id, price):
            return await ctx.send(f"{user.mention}, you're too poor to buy this item!")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
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
    @user_cooldown(10)
    @commands.command(aliases=["merch"])
    async def merchant(self, ctx, itemid: int):
        """Sells an item for its value."""
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(f"You don't own an item with the ID: {itemid}")
            if item["equipped"]:
                if not await ctx.confirm(
                    f"Are you sure you want to sell your equipped {item['name']}?",
                    timeout=6,
                ):
                    return await ctx.send("Cancelled.")
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                item["price"],
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
            money, count = await conn.fetchval(
                "SELECT (sum(value), count(value)) FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE ai.owner=$1 AND i.equipped IS FALSE;",
                ctx.author.id,
            )
            if count == 0:
                return await ctx.send("Nothing to merch.")
            await conn.execute(
                "DELETE FROM allitems ai USING inventory i WHERE ai.id=i.item AND ai.owner=$1 AND i.equipped IS FALSE;",
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
        await ctx.send(f"Merched **{count}** items for **${money}**.")

    @commands.command()
    async def pending(self, ctx):
        """View your pending shop offers."""
        async with self.bot.pool.acquire() as conn:
            items = await conn.fetch(
                'SELECT * FROM allitems ai JOIN market m ON (m.item=ai.id) WHERE ai."owner"=$1;',
                ctx.author.id,
            )
        if not items:
            return await ctx.send("You don't have any pending shop offers.")
        items = [
            discord.Embed(
                title="IdleRPG Shop",
                description=f"Use `{ctx.prefix}buy {item['id']}` to buy this.",
                colour=discord.Colour.blurple(),
            )
            .add_field(name="Name", value=item["name"])
            .add_field(name="Type", value=item["type"])
            .add_field(name="Damage", value=item["damage"])
            .add_field(name="Armor", value=item["armor"])
            .add_field(name="Value", value=f"${item['value']}")
            .add_field(name="Price", value=f"${item['price']}")
            .set_footer(text=f"Item {idx + 1} of {len(items)}")
            for idx, item in enumerate(items)
        ]
        await self.bot.paginator.Paginator(extras=items).paginate(ctx)

    @has_char()
    @user_cooldown(3600)
    @commands.command()
    async def trader(self, ctx):
        """Buy items at the trader."""
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

        offerid = await self.bot.paginator.Choose(
            title="The Trader",
            footer="Hit a button to buy it",
            return_index=True,
            entries=[
                f"**{i[4]} - {i[1] if i[0] == 'Sword' else i[2]} {'Damage' if i[0] == 'Sword' else 'Armor'} - **${i[5]}**"
                for i in offers
            ],
        ).paginate(ctx)

        item = offers[offerid]
        if not await has_money(self.bot, ctx.author.id, item[5]):
            return await ctx.send("You are too poor to buy this item.")
        await self.bot.pool.execute(
            'UPDATE profile SET money=money-$1 WHERE "user"=$2;', item[5], ctx.author.id
        )
        await self.bot.create_item(
            type_=item[0],
            damage=item[1],
            armor=item[2],
            value=item[3],
            name=item[4],
            owner=ctx.author,
        )
        await ctx.send(
            f"Successfully bought offer **{offerid+1}**. Use `{ctx.prefix}inventory` to view your updated inventory."
        )


def setup(bot):
    bot.add_cog(Trading(bot))
