"""
The IdleRPG Discord Bot
Copyright (C) 2018-2021 Diniboy and Gelbpunkt

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

from collections import defaultdict

import discord

from discord.ext import commands

from classes.converters import CrateRarity, IntGreaterThan, MemberWithCharacter
from utils.i18n import _, locale_doc


def has_no_transaction():
    async def predicate(ctx):
        return not ctx.bot.cogs["Transaction"].get_transaction(ctx.author)

    return commands.check(predicate)


def has_transaction():
    async def predicate(ctx):
        ctx.transaction = ctx.bot.cogs["Transaction"].get_transaction(ctx.author)
        return ctx.transaction

    return commands.check(predicate)


class Transaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.transactions = {}

    def get_transaction(self, user, return_id=False):
        id_ = str(user.id)
        if not (key := discord.utils.find(lambda x: id_ in x, self.transactions)):
            return None
        if return_id:
            return key
        return self.transactions[key]["content"][user]

    async def update(self, ctx):
        id_ = self.get_transaction(ctx.author, return_id=True)
        content = "\n\n".join(
            [
                _(
                    """\
> {user} gives:
{money}{crates}{items}"""
                ).format(
                    user=user.mention,
                    money=f"- **${m}**\n" if (m := cont["money"]) else "",
                    crates="".join(
                        [
                            f"- **{i}** {getattr(self.bot.cogs['Crates'].emotes, j)}\n"
                            for j, i in cont["crates"].items()
                        ]
                    ),
                    items="".join(
                        [
                            f"- {i['name']} ({i['type']}, {i['damage'] + i['armor']})\n"
                            for i in cont["items"]
                        ]
                    ),
                )
                for user, cont in self.transactions[id_]["content"].items()
            ]
        )
        content = (
            content
            + "\n\n"
            + _(
                "Use `{prefix}trade [add/set/remove] [money/crates/item]"
                " [amount/itemid] [crate rarity]`"
            ).format(prefix=ctx.prefix)
        )
        if (base := self.transactions[id_]["base"]) is not None:
            await base.delete()
        self.transactions[id_]["base"] = await ctx.send(content)
        if (task := self.transactions[id_]["task"]) is not None:
            task.cancel()
        self.transactions[id_]["task"] = self.bot.loop.create_task(
            self.task(self.transactions[id_])
        )

    async def task(self, trans):
        msg = trans["base"]
        users = list(trans["content"].keys())
        key = "-".join([str(u.id) for u in users])
        acc = []
        reacts = ["\U0000274e", "\U00002705"]
        for r in reacts:
            await msg.add_reaction(r)

        def check(r, u):
            return (
                u in users
                and r.emoji in reacts
                and r.message.id == msg.id
                and u not in acc
            )

        while len(acc) < 2:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            except asyncio.TimeoutError:
                await msg.delete()
                del self.transactions[key]
                return await msg.channel.send(_("Trade timed out."))
            if reacts.index(r.emoji):
                acc.append(u)
            else:
                await msg.delete()
                del self.transactions[key]
                return await msg.channel.send(
                    _("{user} stopped the trade.").format(user=u.mention)
                )
        del self.transactions[key]
        await self.transact(trans)

    async def transact(self, trans):
        chan = (base := trans["base"]).channel
        await base.delete()
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                # Lock both users for now
                (user1, user1_gives), (user2, user2_gives) = trans["content"].items()
                user1_item_ids = [i["id"] for i in user1_gives["items"]]
                user2_item_ids = [i["id"] for i in user2_gives["items"]]
                user1_row = await conn.fetchrow(
                    'SELECT * FROM profile WHERE "user"=$1 FOR UPDATE;', user1.id
                )
                user2_row = await conn.fetchrow(
                    'SELECT * FROM profile WHERE "user"=$1 FOR UPDATE;', user2.id
                )
                # Lock their traded items
                user1_items = (
                    await conn.fetch(
                        "SELECT * FROM allitems ai JOIN inventory i ON"
                        ' (ai."id"=i."item") WHERE ai."id"=ANY($1) AND ai."owner"=$2'
                        " FOR UPDATE;",
                        user1_item_ids,
                        user1.id,
                    )
                    or []
                )
                user2_items = (
                    await conn.fetch(
                        "SELECT * FROM allitems ai JOIN inventory i ON"
                        ' (ai."id"=i."item") WHERE ai."id"=ANY($1) AND ai."owner"=$2'
                        " FOR UPDATE;",
                        user2_item_ids,
                        user2.id,
                    )
                    or []
                )
                relative_money_difference_user1 = user2_gives.get(
                    "money", 0
                ) - user1_gives.get("money", 0)
                relative_money_difference_user2 = user1_gives.get(
                    "money", 0
                ) - user2_gives.get("money", 0)
                # Just to normalize
                all_crate_rarities = {
                    "common": 0,
                    "uncommon": 0,
                    "rare": 0,
                    "magic": 0,
                    "legendary": 0,
                }
                normalized_crates_user1 = all_crate_rarities | user1_gives["crates"]
                normalized_crates_user2 = all_crate_rarities | user2_gives["crates"]
                relative_crate_difference_user1 = {
                    r: a - normalized_crates_user1[r]
                    for r, a in normalized_crates_user2.items()
                }
                relative_crate_difference_user2 = {
                    r: a - normalized_crates_user2[r]
                    for r, a in normalized_crates_user1.items()
                }
                profile_cols_to_change_user1 = {
                    f"crates_{col}": val
                    for col, val in relative_crate_difference_user1.items()
                    if val
                }
                if relative_money_difference_user1:
                    profile_cols_to_change_user1[
                        "money"
                    ] = relative_money_difference_user1
                profile_cols_to_change_user2 = {
                    f"crates_{col}": val
                    for col, val in relative_crate_difference_user2.items()
                    if val
                }
                if relative_money_difference_user2:
                    profile_cols_to_change_user2[
                        "money"
                    ] = relative_money_difference_user2
                # Now, verify nothing has been traded away
                # Items are most obvious
                if len(user1_items) < len(user1_gives["items"]) or len(
                    user2_items
                ) < len(user2_gives["items"]):
                    return await chan.send(
                        _("Trade cancelled. Things were traded away in the meantime.")
                    )
                if any(
                    [
                        (item["original_name"] or item["original_type"])
                        for item in user1_items
                    ]
                ) or any(
                    [
                        (item["original_name"] or item["original_type"])
                        for item in user2_items
                    ]
                ):
                    return await chan.send(
                        _("Some item was modified in the meanwhile.")
                    )
                # Profile columns need to be checked if they are negative and substracting would be negative
                for col, val in profile_cols_to_change_user1.items():
                    if (
                        val < 0 and user1_row[col] + val < 0
                    ):  # substracting is smaller 0
                        return await chan.send(
                            _(
                                "Trade cancelled. Things were traded away in the"
                                " meantime."
                            )
                        )
                for col, val in profile_cols_to_change_user2.items():
                    if val < 0 and user2_row[col] + val < 0:
                        return await chan.send(
                            _(
                                "Trade cancelled. Things were traded away in the"
                                " meantime."
                            )
                        )

                # Everything OK, do transaction
                if user1_items:
                    await conn.execute(
                        'UPDATE allitems SET "owner"=$1 WHERE "id"=ANY($2);',
                        user2.id,
                        user1_item_ids,
                    )
                    await conn.execute(
                        'UPDATE inventory SET "equipped"=$1 WHERE "item"=ANY($2);',
                        False,
                        user1_item_ids,
                    )
                if user2_items:
                    await conn.execute(
                        'UPDATE allitems SET "owner"=$1 WHERE "id"=ANY($2);',
                        user1.id,
                        user2_item_ids,
                    )
                    await conn.execute(
                        'UPDATE inventory SET "equipped"=$1 WHERE "item"=ANY($2);',
                        False,
                        user2_item_ids,
                    )

                row_string_user1 = ", ".join(
                    [
                        f'"{col}"="{col}"+${n + 1}'
                        if val > 0
                        else f'"{col}"="{col}"-${n + 1}'
                        for n, (col, val) in enumerate(
                            profile_cols_to_change_user1.items()
                        )
                    ]
                )
                row_string_user2 = ", ".join(
                    [
                        f'"{col}"="{col}"+${n + 1}'
                        if val > 0
                        else f'"{col}"="{col}"-${n + 1}'
                        for n, (col, val) in enumerate(
                            profile_cols_to_change_user2.items()
                        )
                    ]
                )
                query_args_user_1 = [
                    abs(i) for i in profile_cols_to_change_user1.values()
                ]
                query_args_user_1.append(user1.id)
                query_args_user_2 = [
                    abs(i) for i in profile_cols_to_change_user2.values()
                ]
                query_args_user_2.append(user2.id)

                n_1 = len(profile_cols_to_change_user1) + 1
                n_2 = len(profile_cols_to_change_user2) + 1

                if profile_cols_to_change_user1:
                    await conn.execute(
                        f'UPDATE profile SET {row_string_user1} WHERE "user"=${n_1};',
                        *query_args_user_1,
                    )
                    await self.bot.cache.update_profile_cols_rel(
                        user1.id, **profile_cols_to_change_user1
                    )
                if profile_cols_to_change_user2:
                    await conn.execute(
                        f'UPDATE profile SET {row_string_user2} WHERE "user"=${n_2};',
                        *query_args_user_2,
                    )
                    await self.bot.cache.update_profile_cols_rel(
                        user2.id, **profile_cols_to_change_user2
                    )

            await chan.send(_("Trade successful."))

    @has_no_transaction()
    @commands.group(
        invoke_without_command=True, brief=_("Opens a trading session with a user.")
    )
    @locale_doc
    async def trade(self, ctx, user: MemberWithCharacter):
        _(
            """Opens a trading session for you and another player.
            Using `{prefix}trade <user>`, then the user accepting the checkbox will start the trading session.

            While the trading session is open, you and the other player can add or remove items, money and crates as you choose.

            Here are some examples to familiarize you with the concept:
             - {prefix}trade add crates 10 common
             - {prefix}trade set money 1000
             - {prefix}trade remove item 13377331 (this only works if you added this item before)
             - {prefix}trade add items 1234 2345 3456

            To accept the trade, both players need to react with the ✅ emoji.
            Accepting the trade will transfer all items in the trade session to the other player.

            You cannot trade with yourself, or have more than one trade session open at once.
            Giving away any items, crates or money during the trade will render it invalid and it will not complete."""
        )
        if user == ctx.author:
            return await ctx.send(_("You cannot trade with yourself."))
        if not await ctx.confirm(
            _("{user} has requested a trade, {user2}.").format(
                user=ctx.author.mention, user2=user.mention
            ),
            user=user,
        ):
            return
        if any([str(user.id) in key for key in self.transactions]) or any(
            [str(ctx.author.id) in key for key in self.transactions]
        ):
            return await ctx.send(_("Someone is already in a trade."))
        identifier = f"{ctx.author.id}-{user.id}"
        self.transactions[identifier] = {
            "content": {
                ctx.author: {"crates": defaultdict(lambda: 0), "money": 0, "items": []},
                user: {"crates": defaultdict(lambda: 0), "money": 0, "items": []},
            },
            "base": None,
            "task": None,
        }
        await self.update(ctx)

    @has_transaction()
    @trade.group(invoke_without_command=True, brief=_("Adds something to a trade."))
    @locale_doc
    async def add(self, ctx):
        _(
            """Adds something to trade session.
            You can specifiy what item you want to add to the trade by using one of the subcommands below.

            You need to have an open trading session to use this command."""
        )
        await ctx.send(
            _(
                "Please select something to add. Example: `{prefix}trade add money"
                " 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @add.command(name="money", brief=_("Adds money to a trade."))
    @locale_doc
    async def add_money(self, ctx, amount: IntGreaterThan(0)):
        _(
            """`<amount>` - The amount of money to add, must be greater than 0

            Adds money to the trading session. You cannot add more money than you have.
            To remove money, consider `{prefix}trade remove money`.

            You need to have an open trading session to use this command."""
        )
        if await self.bot.has_money(ctx.author.id, ctx.transaction["money"] + amount):
            ctx.transaction["money"] += amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You are too poor."))

    @has_transaction()
    @add.command(name="crates", brief=_("Adds crates to a trade."))
    @locale_doc
    async def add_crates(self, ctx, amount: IntGreaterThan(0), rarity: CrateRarity):
        _(
            """`<amount>` - The amount of crates to add, must be greater than 0
            `<rarity>` - The crate rarity to add, can be common, uncommon, rare, magic or legendary

            Adds crate to the trading session. You cannot add more crates than you have.
            To remove crates, consider `{prefix}trade remove crates`.

            You need to have an open trading session to use this command."""
        )
        if await self.bot.has_crates(
            ctx.author.id, ctx.transaction["crates"][rarity] + amount, rarity
        ):
            ctx.transaction["crates"][rarity] += amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not have enough crates."))

    @has_transaction()
    @add.command(name="item", brief=_("Adds items to a trade."))
    @locale_doc
    async def add_item(self, ctx, itemid: int):
        _(
            """`<itemid>` - The ID of the item to add

            Add an item to the trading session. The item needs to be in your inevntory.
            To remove an item, consider `{prefix}trade remove item`.

            You need to have an open trading session to use this command."""
        )
        if itemid in [x["id"] for x in ctx.transaction["items"]]:
            return await ctx.send(_("You already added this item!"))
        if item := await self.bot.pool.fetchrow(
            'SELECT ai.* FROM allitems ai JOIN inventory i ON (ai."id"=i."item") WHERE'
            ' ai."id"=$1 AND ai."owner"=$2;',
            itemid,
            ctx.author.id,
        ):
            if item["original_name"] or item["original_type"]:
                return await ctx.send(_("You may not sell modified items."))
            ctx.transaction["items"].append(item)
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not own this item."))

    @has_transaction()
    @add.command(name="items", brief=_("Adds multiple items to a trade."))
    @locale_doc
    async def add_items(self, ctx, *itemids: int):
        _(
            """`<itemids...>` - The IDs of the item to add, separated by space

            Adds multiple items to the trading session. The items cannot already be in the trading session.
            Items that are not in your inventory will be automatically filtered out.
            To remove an item, consider `{prefix}trade remove item`.

            You need to have an open trading session to use this command."""
        )
        if any([(x in [x["id"] for x in ctx.transaction["items"]]) for x in itemids]):
            return await ctx.send(_("You already added one or more of these items!"))
        items = await self.bot.pool.fetch(
            'SELECT ai.* FROM allitems ai JOIN inventory i ON (ai."id"=i."item") WHERE'
            ' ai."id"=ANY($1) AND ai."owner"=$2;',
            itemids,
            ctx.author.id,
        )
        for item in items:
            if item["original_name"] or item["original_type"]:
                return await ctx.send(_("You may not sell modified items."))
            ctx.transaction["items"].append(item)
        await ctx.message.add_reaction(":blackcheck:441826948919066625")

    @has_transaction()
    @trade.group(
        invoke_without_command=True,
        name="set",
        brief=_("Sets a value to a trade instead of adding onto it."),
    )
    @locale_doc
    async def set_(self, ctx):
        _(
            """Sets a sepcific value in the trade session.
            You can specifiy what item you want to set in the trade by using one of the subcommands below.

            You need to have an open trading session to use this command."""
        )
        await ctx.send(
            _(
                "Please select something to set. Example: `{prefix}trade set money"
                " 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @set_.command(name="money", brief=_("Sets money in a trade."))
    @locale_doc
    async def set_money(self, ctx, amount: IntGreaterThan(-1)):
        _(
            """`<amount>` - The amount of money to set, must be greater than -1

            Sets an amount of money in the trading session. You cannot set more money than you have.
            To add or remove money, consider `{prefix}trade add/remove money`.

            You need to have an open trading session to use this command."""
        )
        if await self.bot.has_money(ctx.author.id, amount):
            ctx.transaction["money"] = amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You are too poor."))

    @has_transaction()
    @set_.command(name="crates", brief=_("Sets crates in a trade."))
    @locale_doc
    async def set_crates(self, ctx, amount: IntGreaterThan(-1), rarity: CrateRarity):
        _(
            """`<amount>` - The amount of crates to set, must be greater than -1
            `<rarity>` - The crate rarity to set, can be common, uncommon, rare, magic or legendary

            Sets an amount of crates in the trading session. You cannot set more crates than you have.
            To add or remove crates, consider `{prefix}trade add/remove crates`.

            You need to have an open trading session to use this command."""
        )
        if await self.bot.has_crates(ctx.author.id, amount, rarity):
            ctx.transaction["crates"][rarity] = amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not have enough crates."))

    @has_transaction()
    @trade.group(
        invoke_without_command=True,
        aliases=["del", "rem", "delete"],
        brief=_("Removes something from a trade."),
    )
    @locale_doc
    async def remove(self, ctx):
        _(
            """Removes something from a trade session.
            You can remove something of your choice by using one of the subcommands below.

            You need to have an open trading session to use this command."""
        )
        await ctx.send(
            _(
                "Please select something to remove. Example: `{prefix}trade remove"
                " money 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @remove.command(name="money", brief=_("Removes money from a trade."))
    @locale_doc
    async def remove_money(self, ctx, amount: IntGreaterThan(0)):
        _(
            """`<amount>` - The amount of money to remove, must be greater than 0

            Removes money from the trading session. You cannot remove more money than you added.
            To add money, consider `{prefix}trade add money`.

            You need to have an open trading session to use this command."""
        )
        if ctx.transaction["money"] - amount >= 0:
            ctx.transaction["money"] -= amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("Resulting amount is negative."))

    @has_transaction()
    @remove.command(name="crates", brief=_("Removes crates from a trade."))
    @locale_doc
    async def remove_crates(self, ctx, amount: IntGreaterThan(0), rarity: CrateRarity):
        _(
            """`<amount>` - The amount of crates to remove, must be greater than 0
            `<rarity>` - The crate rarity to remove, can be common, uncommon, rare, magic or legendary

            Removes crates from the trading session. You cannot remove more crates than you added.
            To add crates, consider `{prefix}trade add crates`.

            You need to have an open trading session to use this command."""
        )
        if (res := ctx.transaction["crates"][rarity] - amount) >= 0:
            if res == 0:
                del ctx.transaction["crates"][rarity]
            else:
                ctx.transaction["crates"][rarity] -= amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("The resulting amount would be negative."))

    @has_transaction()
    @remove.command(name="item", brief=_("Removes items from a trade."))
    @locale_doc
    async def remove_item(self, ctx, itemid: int):
        _(
            """`<itemid>` - The ID of the item to remove

            Remove an item from the trading session. The item needs to be in the trade to remove it.
            To add an item, consider `{prefix}trade add item`.

            You need to have an open trading session to use this command."""
        )
        item = discord.utils.find(lambda x: x["id"] == itemid, ctx.transaction["items"])
        if item:
            ctx.transaction["items"].remove(item)
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("This item is not in the trade."))

    @has_transaction()
    @remove.command(name="items", brief=_("Removes multiple items to a trade."))
    @locale_doc
    async def remove_items(self, ctx, *itemids: int):
        _(
            """`<itemids...>` - The IDs of the item to remove, separated by space

            Remove multiple items from the trading session. The items must be in the trading session already.
            Items that are not in the trade will be automatically filtered out.
            To remove an item, consider `{prefix}trade remove item`.

            You need to have an open trading session to use this command."""
        )
        for itemid in itemids:
            item = discord.utils.find(
                lambda x: x["id"] == itemid, ctx.transaction["items"]
            )
            if item:
                ctx.transaction["items"].remove(item)
        await ctx.message.add_reaction(":blackcheck:441826948919066625")

    async def cog_after_invoke(self, ctx):
        if hasattr(ctx, "transaction"):
            await self.update(ctx)


def setup(bot):
    bot.add_cog(Transaction(bot))
