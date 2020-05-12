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
import discord

from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_money
from utils.i18n import _, locale_doc
from utils.paginator import NoChoice


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.markdown_escaper = commands.clean_content(escape_markdown=True)

    @has_char()
    @commands.command()
    @locale_doc
    async def sell(self, ctx, itemid: int, price: IntGreaterThan(-1)):
        _(
            """Puts your item into the market. Tax for selling items is 5% of the price."""
        )
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    _("You don't own an item with the ID: {itemid}").format(
                        itemid=itemid
                    )
                )
            if item["original_name"] or item["original_type"]:
                return await ctx.send(_("You may not sell donator-modified items."))
            if item["value"] > price:
                return await ctx.send(
                    _(
                        "Selling an item below its value is a bad idea. You can always"
                        " do `{prefix}merchant {itemid}` to get more money."
                    ).format(prefix=ctx.prefix, itemid=itemid)
                )
            elif item["damage"] < 4 and item["armor"] < 4:
                return await ctx.send(
                    _(
                        "Your item is either equal to a Starter Item or worse. Noone"
                        " would buy it."
                    )
                )
            if (
                builds := await self.bot.get_city_buildings(ctx.character_data["guild"])
            ) and builds["trade_building"] != 0:
                tax = 0
            else:
                tax = round(price * 0.05)
            if ctx.character_data["money"] < tax:
                return await ctx.send(
                    _("You cannot afford the tax of 5% (${amount}).").format(amount=tax)
                )
            if tax:
                await conn.execute(
                    'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                    tax,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": tax},
                )
            await conn.execute(
                "DELETE FROM inventory i USING allitems ai WHERE i.item=ai.id AND"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO market (item, price) VALUES ($1, $2);", itemid, price
            )
        await ctx.send(
            _(
                "Successfully added your item to the shop! Use `{prefix}shop` to view"
                " it in the market! {additional}"
            ).format(
                prefix=ctx.prefix,
                additional=_("The tax of 5% has been deducted from your account.")
                if not builds or builds["trade_building"] == 0
                else "",
            )
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def buy(self, ctx, itemid: int):
        _("""Buys an item from the global market.""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                'SELECT *, m."id" AS "offer" FROM market m JOIN allitems ai ON'
                ' (m."item"=ai."id") WHERE ai."id"=$1;',
                itemid,
            )
            if not item:
                return await ctx.send(
                    _("There is no item in the shop with the ID: {itemid}").format(
                        itemid=itemid
                    )
                )
            if item["owner"] == ctx.author.id:
                return await ctx.send(_("You may not buy your own items."))
            if await self.bot.get_city_buildings(ctx.character_data["guild"]):
                tax = 0
            else:
                tax = round(item["price"] * 0.05)
            if ctx.character_data["money"] < item["price"] + tax:
                return await ctx.send(_("You're too poor to buy this item."))
            await conn.execute(
                "DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=$1"
                " RETURNING *;",
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
                item["price"] + tax,
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO inventory (item, equipped) VALUES ($1, $2);",
                item["id"],
                False,
            )
            if tax:
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": item["price"] + tax},
                )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=item["owner"],
                subject="money",
                data={"Amount": item["price"]},
            )
        await ctx.send(
            _(
                "Successfully bought item `{id}`. Use `{prefix}inventory` to view your"
                " updated inventory."
            ).format(id=item["id"], prefix=ctx.prefix)
        )
        seller = await self.bot.get_user_global(item["owner"])
        if seller:
            await seller.send(
                "**{author}** bought your **{name}** for **${price}** from the market."
                .format(author=ctx.author.name, name=item["name"], price=item["price"])
            )
        await self.bot.log_transaction(
            ctx,
            from_=(seller if seller else item["owner"]),
            to=ctx.author,
            subject="shop",
            data=item,
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def remove(self, ctx, itemid: int):
        _("""Takes an item off the shop.""")
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM market m JOIN allitems ai ON (m.item=ai.id) WHERE"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    _(
                        "You don't have an item of yours in the shop with the ID"
                        " `{itemid}`."
                    ).format(itemid=itemid)
                )
            await conn.execute(
                "DELETE FROM market m USING allitems ai WHERE m.item=ai.id AND ai.id=$1"
                " AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            await conn.execute(
                "INSERT INTO inventory (item, equipped) VALUES ($1, $2);", itemid, False
            )
        await ctx.send(
            _(
                "Successfully removed item `{itemid}` from the shop and put it in your"
                " inventory."
            ).format(itemid=itemid)
        )

    @commands.command(aliases=["market", "m"])
    @locale_doc
    async def shop(
        self,
        ctx,
        itemtype: str.title = "All",
        minstat: float = 0.00,
        highestprice: IntGreaterThan(-1) = 1_000_000,
    ):
        _("""Lists the buyable items on the market.""")
        if itemtype not in ["All"] + self.bot.config.item_types:
            return await ctx.send(
                _("Use either {types} or `All` as a type to filter for.").format(
                    types=", ".join(f"`{t}`" for t in self.bot.config.item_types)
                )
            )
        if itemtype == "All":
            items = await self.bot.pool.fetch(
                "SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE"
                ' m."price"<=$1 AND (ai."damage">=$2 OR ai."armor">=$3);',
                highestprice,
                minstat,
                minstat,
            )
        elif itemtype == "Shield":
            items = await self.bot.pool.fetch(
                "SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE"
                ' ai."type"=$1 AND ai."armor">=$2 AND m."price"<=$3;',
                itemtype,
                minstat,
                highestprice,
            )
        else:
            items = await self.bot.pool.fetch(
                "SELECT * FROM allitems ai JOIN market m ON (ai.id=m.item) WHERE"
                ' ai."type"=$1 AND ai."damage">=$2 AND m."price"<=$3;',
                itemtype,
                minstat,
                highestprice,
            )
        if not items:
            return await ctx.send(_("No results."))

        items = [
            discord.Embed(
                title=_("IdleRPG Shop"),
                description=_("Use `{prefix}buy {item}` to buy this.").format(
                    prefix=ctx.prefix, item=item["item"]
                ),
                colour=discord.Colour.blurple(),
            )
            .add_field(name=_("Name"), value=item["name"])
            .add_field(name=_("Type"), value=item["type"])
            .add_field(name=_("Damage"), value=item["damage"])
            .add_field(name=_("Armor"), value=item["armor"])
            .add_field(name=_("Value"), value=f"${item['value']}")
            .add_field(
                name=_("Price"),
                value=f"${item['price']} (+${round(item['price'] * 0.05)} (5%) tax)",
            )
            .set_footer(
                text=_("Item {num} of {total}").format(num=idx + 1, total=len(items))
            )
            for idx, item in enumerate(items)
        ]

        await self.bot.paginator.Paginator(extras=items).paginate(ctx)

    @has_char()
    @user_cooldown(180)
    @commands.command()
    @locale_doc
    async def offer(
        self, ctx, itemid: int, price: IntFromTo(0, 100_000_000), user: discord.Member
    ):
        _("""Offer an item to a specific user.""")
        if user == ctx.author:
            return await ctx.send(_("You may not offer items to yourself."))
        item = await self.bot.pool.fetchrow(
            "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
            " ai.id=$1 AND ai.owner=$2;",
            itemid,
            ctx.author.id,
        )
        if not item:
            return await ctx.send(
                _("You don't have an item with the ID `{itemid}`.").format(
                    itemid=itemid
                )
            )

        if item["original_name"] or item["original_type"]:
            return await ctx.send(_("You may not sell donator-modified items."))

        if item["equipped"]:
            if not await ctx.confirm(
                _("Are you sure you want to sell your equipped {item}?").format(
                    item=item["name"]
                )
            ):
                return await ctx.send(_("Item selling cancelled."))

        if not await ctx.confirm(
            _(
                "{user}, {author} offered you an item! React to buy it! The price is"
                " **${price}**. You have **2 Minutes** to accept the trade or the offer"
                " will be canceled."
            ).format(user=user.mention, author=ctx.author.mention, price=price),
            user=user,
            timeout=120,
        ):
            return await ctx.send(_("They didn't want it."))

        if not await has_money(self.bot, user.id, price):
            return await ctx.send(
                _("{user}, you're too poor to buy this item!").format(user=user.mention)
            )
        async with self.bot.pool.acquire() as conn:
            item = await conn.fetchrow(
                "SELECT * FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
                " ai.id=$1 AND ai.owner=$2;",
                itemid,
                ctx.author.id,
            )
            if not item:
                return await ctx.send(
                    _(
                        "The owner sold the item with the ID `{itemid}` in the"
                        " meantime."
                    ).format(itemid=itemid)
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
        await self.bot.log_transaction(
            ctx,
            from_=ctx.author.id,
            to=user.id,
            subject="item",
            data={"Name": item["name"], "Value": item["value"]},
        )
        await ctx.send(
            _(
                "Successfully bought item `{itemid}`. Use `{prefix}inventory` to view"
                " your updated inventory."
            ).format(itemid=itemid, prefix=ctx.prefix)
        )

        await self.bot.log_transaction(
            ctx, from_=ctx.author, to=user, subject="offer", data=item
        )

    @has_char()
    @user_cooldown(600)  # prevent too long sale times
    @commands.command(aliases=["merch"])
    @locale_doc
    async def merchant(self, ctx, *itemids: int):
        _("""Sells items for their value.""")
        if not itemids:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You cannot sell nothing."))
        async with self.bot.pool.acquire() as conn:
            value, amount, equipped = await conn.fetchval(
                "SELECT (sum(ai.value), count(*), SUM(CASE WHEN i.equipped THEN 1 END))"
                " FROM inventory i JOIN allitems ai ON (i.item=ai.id) WHERE"
                " ai.id=ANY($1) AND ai.owner=$2;",
                itemids,
                ctx.author.id,
            )
            if not amount:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("You don't own any items with the IDs: {itemids}").format(
                        itemids=", ".join([str(itemid) for itemid in itemids])
                    )
                )

            if equipped:
                if not await ctx.confirm(
                    _(
                        "You are about to sell {amount} equipped items. Are you sure?"
                    ).format(amount=equipped),
                    timeout=6,
                ):
                    return await ctx.send(_("Cancelled."))
            if (
                buildings := await self.bot.get_city_buildings(
                    ctx.character_data["guild"]
                )
            ) :
                value = value * (1 + buildings["trade_building"] / 2)
            await conn.execute(
                'DELETE FROM allitems WHERE "id"=ANY($1) AND "owner"=$2;',
                itemids,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                value,
                ctx.author.id,
            )
        await self.bot.log_transaction(
            ctx,
            from_=1,
            to=ctx.author.id,
            subject="merch",
            data={"Amount": f"{len(itemids)} items", "Value": value},
        )
        await ctx.send(
            _(
                "You received **${money}** when selling item(s) `{itemids}`."
                " {additional}"
            ).format(
                money=value,
                itemids=", ".join([str(itemid) for itemid in itemids]),
                additional=_(
                    "Skipped `{amount}` because they did not belong to you."
                ).format(amount=len(itemids) - amount)
                if len(itemids) > amount
                else "",
            )
        )
        await self.bot.reset_cooldown(ctx)  # we finished

    @has_char()
    @user_cooldown(1800)
    @commands.command(enabled=False)
    @locale_doc
    async def merchall(
        self, ctx, maxstat: IntFromTo(0, 75) = 75, minstat: IntFromTo(0, 75) = 0
    ):
        _("""Sells all your non-equipped items for their value.""")
        async with self.bot.pool.acquire() as conn:
            money, count = await conn.fetchval(
                "SELECT (sum(value), count(value)) FROM inventory i JOIN allitems ai ON"
                " (i.item=ai.id) WHERE ai.owner=$1 AND i.equipped IS FALSE AND"
                " ai.armor+ai.damage BETWEEN $2 AND $3;",
                ctx.author.id,
                minstat,
                maxstat,
            )
            if count == 0:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(_("Nothing to merch."))
            if (
                buildings := await self.bot.get_city_buildings(
                    ctx.character_data["guild"]
                )
            ) :
                money = int(money * (1 + buildings["trade_building"] / 2))
            if not await ctx.confirm(
                _(
                    "You are about to sell **{count} items for ${money}!**\nAre you"
                    " sure you want to do this?"
                ).format(count=count, money=money)
            ):
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(_("Cancelled selling your items."))
            newcount = await self.bot.pool.fetchval(
                "SELECT count(value) FROM inventory i JOIN allitems ai ON"
                " (i.item=ai.id) WHERE ai.owner=$1 AND i.equipped IS FALSE AND"
                " ai.armor+ai.damage BETWEEN $2 AND $3;",
                ctx.author.id,
                minstat,
                maxstat,
            )
            if newcount != count:
                await ctx.send(
                    _(
                        "Looks like you got more or less items in that range in the"
                        " meantime. Please try again."
                    )
                )
                return await self.bot.reset_cooldown(ctx)
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM allitems ai USING inventory i WHERE ai.id=i.item AND"
                    " ai.owner=$1 AND i.equipped IS FALSE AND ai.armor+ai.damage"
                    " BETWEEN $2 AND $3;",
                    ctx.author.id,
                    minstat,
                    maxstat,
                )
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
            await self.bot.log_transaction(
                ctx,
                from_=1,
                to=ctx.author.id,
                subject="merch",
                data={"Amount": f"{count} items", "Value": money},
            )
            await ctx.send(
                _("Merched **{count}** items for **${money}**.").format(
                    count=count, money=money
                )
            )

    @commands.command()
    @locale_doc
    async def pending(self, ctx):
        _("""View your pending shop offers.""")
        items = await self.bot.pool.fetch(
            "SELECT * FROM allitems ai JOIN market m ON (m.item=ai.id) WHERE"
            ' ai."owner"=$1;',
            ctx.author.id,
        )
        if not items:
            return await ctx.send(_("You don't have any pending shop offers."))
        items = [
            discord.Embed(
                title=_("Your pending items"),
                description=_("Use `{prefix}buy {item}` to buy this.").format(
                    prefix=ctx.prefix, item=item["item"]
                ),
                colour=discord.Colour.blurple(),
            )
            .add_field(name=_("Name"), value=item["name"])
            .add_field(name=_("Type"), value=item["type"])
            .add_field(name=_("Damage"), value=item["damage"])
            .add_field(name=_("Armor"), value=item["armor"])
            .add_field(name=_("Value"), value=f"${item['value']}")
            .add_field(name=_("Price"), value=f"${item['price']}")
            .set_footer(
                text=_("Item {num} of {total}").format(num=idx + 1, total=len(items))
            )
            for idx, item in enumerate(items)
        ]
        await self.bot.paginator.Paginator(extras=items).paginate(ctx)

    @has_char()
    @user_cooldown(3600)
    @commands.command()
    @locale_doc
    async def trader(self, ctx):
        _("""Buys items at the trader.""")
        offers = []
        for i in range(5):
            item = await self.bot.create_random_item(
                minstat=1,
                maxstat=15,
                minvalue=1,
                maxvalue=1,
                owner=ctx.author,
                insert=False,
            )
            price = item["armor"] * 50 + item["damage"] * 50
            offers.append((item, price))

        try:
            offerid = await self.bot.paginator.Choose(
                title=_("The Trader"),
                footer=_("Hit a button to buy it"),
                return_index=True,
                entries=[
                    f"**{i[0]['name']}** ({i[0]['type_']}) -"
                    f" {i[0]['armor'] if i[0]['type_'] == 'Shield' else i[0]['damage']}"
                    f" {'armor' if i[0]['type_'] == 'Shield' else 'damage'} -"
                    f" **${i[1]}**"
                    for i in offers
                ],
            ).paginate(ctx)
        except NoChoice:  # prevent cooldown reset
            return await ctx.send(_("You did not choose anything."))

        item = offers[offerid]
        if not await has_money(self.bot, ctx.author.id, item[1]):
            return await ctx.send(_("You are too poor to buy this item."))
        await self.bot.pool.execute(
            'UPDATE profile SET money=money-$1 WHERE "user"=$2;', item[1], ctx.author.id
        )
        await self.bot.log_transaction(
            ctx,
            from_=1,
            to=ctx.author.id,
            subject="item",
            data={"Name": item[0]["name"], "Value": item[0]["value"], "Price": item[1]},
        )
        await self.bot.create_item(**item[0])
        await ctx.send(
            _(
                "Successfully bought offer **{offer}**. Use `{prefix}inventory` to view"
                " your updated inventory."
            ).format(offer=offerid + 1, prefix=ctx.prefix)
        )


def setup(bot):
    bot.add_cog(Trading(bot))
