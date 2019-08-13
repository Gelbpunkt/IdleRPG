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
from collections import defaultdict

import discord
from discord.ext import commands

from classes.converters import CrateRarity, IntGreaterThan, MemberWithCharacter


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
{user} gives:
{money}{crates}{items}"""
                ).format(
                    user=user.mention,
                    money=f"**${m}**\n" if (m := cont["money"]) else "",
                    crates="\n".join(
                        [
                            f"- **{i}** {getattr(self.bot.cogs['Crates'].emojis, j)}"
                            for j, i in cont["crates"].items()
                        ]
                    ),
                    items="\n".join(
                        [
                            f"- {i['name']} ({i['type']}, {i['damage'] + i['armor']})"
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
                "Use `{prefix}trade add/set/remove money/crates/item amount/itemid [crate rarity]`"
            ).format(prefix=ctx.prefix)
        )
        if (base := self.transactions[id_]["base"]) is None:
            self.transactions[id_]["base"] = await ctx.send(content)
        else:
            await base.edit(content=content)

    @has_no_transaction()
    @commands.group(invoke_without_command=True)
    @locale_doc
    async def trade(self, ctx, user: MemberWithCharacter):
        _("""Opens a trading session with a user.""")
        if user == ctx.author:
            return await ctx.send(_("You cannot trade with yourself."))
        if not await ctx.confirm(
            _("{user} has requested a trade, {user2}.").format(
                user=ctx.author.mention, user2=user.mention
            ),
            user=user,
        ):
            return
        identifier = f"{ctx.author.id}-{user.id}"
        self.transactions[identifier] = {
            "content": {
                ctx.author: {"crates": defaultdict(lambda: 0), "money": 0, "items": []},
                user: {"crates": defaultdict(lambda: 0), "money": 0, "items": []},
            },
            "base": None,
        }
        await self.update(ctx)

    @has_transaction()
    @trade.group(invoke_without_command=True)
    @locale_doc
    async def add(self, ctx):
        _("""Adds something to a trade.""")
        await ctx.send(
            _(
                "Please select something to add. Example: `{prefix}trade add money 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @add.command(name="money")
    @locale_doc
    async def add_money(self, ctx, amount: IntGreaterThan(0)):
        _("""Adds money to a trade.""")
        if await self.bot.has_money(ctx.author.id, ctx.transaction["money"] + amount):
            ctx.transaction["money"] += amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You are too poor."))

    @has_transaction()
    @add.command(name="crates")
    @locale_doc
    async def add_crates(self, ctx, amount: IntGreaterThan(0), rarity: CrateRarity):
        _("""Adds crates to a trade.""")
        if await self.bot.has_crates(
            ctx.author.id, ctx.transaction["crates"][rarity] + amount, rarity
        ):
            ctx.transaction["crates"][rarity] += amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not have enough crates."))

    @has_transaction()
    @add.command(name="item")
    @locale_doc
    async def add_item(self, ctx, itemid: int):
        _("""Adds items to a trade.""")
        if (item := await self.bot.has_item(ctx.author.id, itemid)) :
            ctx.transaction["items"].append(item)
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not own this item."))

    @has_transaction()
    @trade.group(invoke_without_command=True, name="set")
    @locale_doc
    async def set_(self, ctx):
        _("""Sets a value to a trade instead of adding onto it.""")
        await ctx.send(
            _(
                "Please select something to set. Example: `{prefix}trade set money 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @set_.command(name="money")
    @locale_doc
    async def set_money(self, ctx, amount: IntGreaterThan(-1)):
        _("""Sets money in a trade.""")
        if await self.bot.has_money(ctx.author.id, amount):
            ctx.transaction["money"] = amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You are too poor."))

    @has_transaction()
    @set_.command(name="crates")
    @locale_doc
    async def set_crates(self, ctx, amount: IntGreaterThan(-1), rarity: CrateRarity):
        _("""Sets crates in a trade.""")
        if await self.bot.has_crates(ctx.author.id, amount, rarity):
            ctx.transaction["crates"][rarity] = amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("You do not have enough crates."))

    @has_transaction()
    @trade.group(invoke_without_command=True, aliases=["del", "rem", "delete"])
    @locale_doc
    async def remove(self, ctx):
        _("""Removes something from a trade.""")
        await ctx.send(
            _(
                "Please select something to remove. Example: `{prefix}trade remove money 1337`"
            ).format(prefix=ctx.prefix)
        )

    @has_transaction()
    @remove.command(name="money")
    @locale_doc
    async def remove_money(self, ctx, amount: IntGreaterThan(0)):
        _("""Removes money from a trade.""")
        if ctx.transaction["money"] - amount >= 0:
            ctx.transaction["money"] -= amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("Resulting amount is negative."))

    @has_transaction()
    @remove.command(name="crates")
    @locale_doc
    async def remove_crates(self, ctx, amount: IntGreaterThan(0), rarity: CrateRarity):
        _("""Removes crates from a trade.""")
        if ctx.transaction["crates"][rarity] - amount >= 0:
            ctx.transaction["crates"][rarity] -= amount
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("The resulting amount would be negative."))

    @has_transaction()
    @remove.command(name="item")
    @locale_doc
    async def remove_item(self, ctx, itemid: int):
        _("""Removes items from a trade.""")
        item = discord.utils.find(lambda x: x["id"] == itemid, ctx.transaction["items"])
        if item:
            ctx.transaction["items"].remove(item)
            await ctx.message.add_reaction(":blackcheck:441826948919066625")
        else:
            await ctx.send(_("This item is not in the trade."))

    async def cog_after_invoke(self, ctx):
        if hasattr(ctx, "transaction"):
            await self.update(ctx)


def setup(bot):
    bot.add_cog(Transaction(bot))
