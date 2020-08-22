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
from collections import Counter, namedtuple

import discord

from discord.ext import commands

from classes.converters import IntFromTo, IntGreaterThan, MemberWithCharacter
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import random
from utils.checks import has_char, has_money
from utils.i18n import _, locale_doc


class Crates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emotes = namedtuple("CrateEmotes", "common uncommon rare magic legendary")(
            common="<:CrateCommon:598094865666015232>",
            uncommon="<:CrateUncommon:598094865397579797>",
            rare="<:CrateRare:598094865485791233>",
            magic="<:CrateMagic:598094865611358209>",
            legendary="<:CrateLegendary:598094865678598144>",
        )

    @has_char()
    @commands.command(aliases=["boxes"], brief=_("Show your crates."))
    @locale_doc
    async def crates(self, ctx):
        _(
            """Shows all the crates you can have.

            Common crates contain items ranging from stats 1 to 30
            Uncommon crates contain items ranging from stats 10 to 35
            Rare crates contain items ranging from stats 20 to 40
            Magic crates contain items ranging from stats 30 to 45
            Legendary crates contain items ranging from stats 41 to 50

            You can receive crates by voting for the bot using `{prefix}vote`, using `{prefix}daily` and with a small chance from `{prefix}familyevent`, if you have children."""
        )
        await ctx.send(
            _(
                """\
**{author}'s crates**

{emotes.common} [common] {common}
{emotes.uncommon} [uncommon] {uncommon}
{emotes.rare} [rare] {rare}
{emotes.magic} [magic] {magic}
{emotes.legendary} [legendary] {legendary}

 Use `{prefix}open [rarity]` to open one!"""
            ).format(
                emotes=self.emotes,
                common=ctx.character_data["crates_common"],
                uncommon=ctx.character_data["crates_uncommon"],
                rare=ctx.character_data["crates_rare"],
                magic=ctx.character_data["crates_magic"],
                legendary=ctx.character_data["crates_legendary"],
                author=ctx.author.mention,
                prefix=ctx.prefix,
            )
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @has_char()
    @commands.command(name="open", brief=_("Open a crate"))
    @locale_doc
    async def _open(
        self, ctx, rarity: str.lower = "common", amount: IntFromTo(1, 100) = 1
    ):
        _(
            """`[rarity]` - the crate's rarity to open, can be common, uncommon, rare, magic or legendary; defaults to common
            `[amount]` - the amount of crates to open, may be in range from 1 to 100 at once

            Open one of your crates to receive a weapon. To check which crates contain which items, check `{prefix}help crates`.
            This command takes up a lot of space, so choose a spammy channel to open crates."""
        )
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        if ctx.character_data[f"crates_{rarity}"] < amount:
            return await ctx.send(
                _(
                    "Seems like you don't have {amount} crate(s) of this rarity yet."
                    " Vote me up to get a random one or find them!"
                ).format(amount=amount)
            )
        # A number to detemine the crate item range
        rand = random.randint(0, 9)
        if rarity == "common":
            if rand < 2:  # 20% 20-30
                minstat, maxstat = (20, 30)
            elif rand < 5:  # 30% 10-19
                minstat, maxstat = (10, 19)
            else:  # 50% 1-9
                minstat, maxstat = (1, 9)
        elif rarity == "uncommon":
            if rand < 2:  # 20% 30-35
                minstat, maxstat = (30, 35)
            elif rand < 5:  # 30% 20-29
                minstat, maxstat = (20, 29)
            else:  # 50% 10-19
                minstat, maxstat = (10, 19)
        elif rarity == "rare":
            if rand < 2:  # 20% 35-40
                minstat, maxstat = (35, 40)
            elif rand < 5:  # 30% 30-34
                minstat, maxstat = (30, 34)
            else:  # 50% 20-29
                minstat, maxstat = (20, 29)
        elif rarity == "magic":
            if rand < 2:  # 20% 41-45
                minstat, maxstat = (41, 45)
            elif rand < 5:  # 30% 35-40
                minstat, maxstat = (35, 40)
            else:
                minstat, maxstat = (30, 34)
        elif rarity == "legendary":  # no else because why
            if rand < 2:  # 20% 49-50
                minstat, maxstat = (49, 50)
            elif rand < 5:  # 30% 46-48
                minstat, maxstat = (46, 48)
            else:  # 50% 41-45
                minstat, maxstat = (41, 45)

        items = []
        async with self.bot.pool.acquire() as conn:
            await self.bot.pool.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"-$1 WHERE'
                ' "user"=$2;',
                amount,
                ctx.author.id,
            )
            await self.bot.cache.update_profile_cols_rel(
                ctx.author.id, **{f"crates_{rarity}": -amount}
            )
            for _i in range(amount):
                item = await self.bot.create_random_item(
                    minstat=minstat,
                    maxstat=maxstat,
                    minvalue=1,
                    maxvalue=250,
                    owner=ctx.author,
                    conn=conn,
                )
                items.append(item)
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="item",
                    data={"Name": item["name"], "Value": item["value"]},
                    conn=conn,
                )
        if amount == 1:
            embed = discord.Embed(
                title=_("You gained an item!"),
                description=_("You found a new item when opening a crate!"),
                color=0xFF0000,
            )
            embed.set_thumbnail(url=ctx.author.avatar_url)
            embed.add_field(name=_("ID"), value=item["id"], inline=False)
            embed.add_field(name=_("Name"), value=item["name"], inline=False)
            embed.add_field(name=_("Type"), value=item["type"], inline=False)
            embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
            embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
            embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
            embed.set_footer(
                text=_("Remaining {rarity} crates: {crates}").format(
                    crates=ctx.character_data[f"crates_{rarity}"] - 1, rarity=rarity
                )
            )
            await ctx.send(embed=embed)
            if rarity == "legendary":
                await self.bot.public_log(
                    f"**{ctx.author}** opened a legendary crate and received"
                    f" {item['name']} with **{item['damage'] or item['armor']}"
                    f" {'damage' if item['damage'] else 'armor'}**."
                )
            elif rarity == "magic" and item["damage"] + item["armor"] >= 41:
                if item["damage"] >= 41:
                    await self.bot.public_log(
                        f"**{ctx.author}** opened a magic crate and received"
                        f" {item['name']} with **{item['damage'] or item['armor']}"
                        f" {'damage' if item['damage'] else 'armor'}**."
                    )
        else:
            stats_raw = [i["damage"] + i["armor"] for i in items]
            stats = Counter(stats_raw)
            types = Counter([i["type"] for i in items])
            most_common = "\n".join(
                [f"- {i[0]} (x{i[1]})" for i in stats.most_common(5)]
            )
            most_common_types = "\n".join(
                [f"- {i[0]} (x{i[1]})" for i in types.most_common()]
            )
            top = "\n".join([f"- {i}" for i in sorted(stats, reverse=True)[:5]])
            average_stat = round(sum(stats_raw) / amount, 2)
            await ctx.send(
                _(
                    "Successfully opened {amount} {rarity} crates. Average stat:"
                    " {average_stat}\nMost common stats:\n```\n{most_common}\n```\nBest"
                    " stats:\n```\n{top}\n```\nTypes:\n```\n{most_common_types}\n```"
                ).format(
                    amount=amount,
                    rarity=rarity,
                    average_stat=average_stat,
                    most_common=most_common,
                    top=top,
                    most_common_types=most_common_types,
                )
            )
            if rarity == "legendary":
                await self.bot.public_log(
                    f"**{ctx.author}** opened {amount} legendary crates and received"
                    f" stats:\n```\n{most_common}\n```\nAverage: {average_stat}"
                )
            elif rarity == "magic":
                await self.bot.public_log(
                    f"**{ctx.author}** opened {amount} magic crates and received"
                    f" stats:\n```\n{most_common}\n```\nAverage: {average_stat}"
                )

    @has_char()
    @commands.command(brief=_("Give crates to someone"))
    @locale_doc
    async def tradecrate(
        self,
        ctx,
        other: MemberWithCharacter,
        amount: IntGreaterThan(0) = 1,
        rarity: str.lower = "common",
    ):
        _(
            """`<other>` - A user with a character
            `[amount]` - A whole number greater than 0; defaults to 1
            `[rarity]` - The crate's rarity to trade, can be common, uncommon, rare, magic or legendary; defaults to common

            Give your crates to another person.

            Players must combine this command with `{prefix}give` for a complete trade."""
        )
        if other == ctx.author:
            return await ctx.send(_("Very funny..."))
        elif other == ctx.me:
            return await ctx.send(
                _("For me? I'm flattered, but I can't accept this...")
            )
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        if ctx.character_data[f"crates_{rarity}"] < amount:
            return await ctx.send(_("You don't have any crates of this rarity."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"-$1 WHERE'
                ' "user"=$2;',
                amount,
                ctx.author.id,
            )
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE'
                ' "user"=$2;',
                amount,
                other.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=other.id,
                subject="crates",
                data={"Rarity": rarity, "Amount": amount},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, **{f"crates_{rarity}": -amount}
        )
        await self.bot.cache.update_profile_cols_rel(
            other.id, **{f"crates_{rarity}": amount}
        )

        await ctx.send(
            _("Successfully gave {amount} {rarity} crate(s) to {other}.").format(
                amount=amount, other=other.mention, rarity=rarity
            )
        )

    @has_char()
    @user_cooldown(180)
    @commands.command(
        aliases=["offercrates", "oc"], brief=_("Offer crates to another player")
    )
    @locale_doc
    async def offercrate(
        self,
        ctx,
        quantity: IntGreaterThan(0),
        rarity: str.lower,
        price: IntFromTo(0, 100_000_000),
        buyer: MemberWithCharacter,
    ):
        _(
            """`<quantity>` - The quantity of crates to offer
            `<rarity>` - The rarity of crate to offer. First letter of the rarity is also accepted.
            `<price>` - The price to be paid by the buyer, can be a number from 0 to 100000000
            `<buyer>` - Another IdleRPG player to offer the crates to

            Offer crates to another player. Once the other player accepts, they will receive the crates and you will receive their payment.
            Example:
            `{prefix}offercrate 5 common 75000 @buyer#1234`
            `{prefix}oc 5 c 75000 @buyer#1234`"""
        )
        if buyer == ctx.author:
            return await ctx.send(_("You may not offer crates to yourself."))
        elif buyer == ctx.me:
            await ctx.send(_("No, I don't want any crates."))
            return await self.bot.reset_cooldown(ctx)

        rarities = {
            "c": "common",
            "u": "uncommon",
            "r": "rare",
            "m": "magic",
            "l": "legendary",
        }
        rarity = rarities.get(rarity, rarity)
        if rarity not in rarities.values():
            await ctx.send(_("{rarity} is not a valid rarity.").format(rarity=rarity))
            return await self.bot.reset_cooldown(ctx)

        if ctx.character_data[f"crates_{rarity}"] < quantity:
            await ctx.send(
                _(
                    "You don't have {quantity} {rarity} crate(s). Check"
                    " `{prefix}crates`."
                ).format(quantity=quantity, rarity=rarity, prefix=ctx.prefix)
            )
            return await self.bot.reset_cooldown(ctx)

        if not await ctx.confirm(
            _(
                "{author}, are you sure you want to offer **{quantity} {emoji}"
                " {rarity}** crate(s) for **${price:,.0f}**?"
            ).format(
                author=ctx.author.mention,
                quantity=quantity,
                emoji=getattr(self.emotes, rarity),
                rarity=rarity,
                price=price,
            )
        ):
            await ctx.send(_("Offer cancelled."))
            return await self.bot.reset_cooldown(ctx)

        try:
            if not await ctx.confirm(
                _(
                    "{buyer}, {author} offered you **{quantity} {emoji} {rarity}**"
                    " crate(s) for **${price:,.0f}!** React to buy it! You have **2"
                    " Minutes** to accept the trade or the offer will be cancelled."
                ).format(
                    buyer=buyer.mention,
                    author=ctx.author.mention,
                    quantity=quantity,
                    emoji=getattr(self.emotes, rarity),
                    rarity=rarity,
                    price=price,
                ),
                user=buyer,
                timeout=120,
            ):
                await ctx.send(
                    _("They didn't want to buy the crate(s). Offer cancelled.")
                )
                return await self.bot.reset_cooldown(ctx)
        except self.bot.paginator.NoChoice:
            await ctx.send(_("They couldn't make up their mind. Offer cancelled."))
            return await self.bot.reset_cooldown(ctx)

        async with self.bot.pool.acquire() as conn:
            if not await has_money(self.bot, buyer.id, price, conn=conn):
                await ctx.send(
                    _("{buyer}, you're too poor to buy the crate(s)!").format(
                        buyer=buyer.mention
                    )
                )
                return await self.bot.reset_cooldown(ctx)
            crates = await self.bot.cache.get_profile_col(
                ctx.author.id, f"crates_{rarity}"
            )
            if crates < quantity:
                return await ctx.send(
                    _(
                        "The seller traded/opened the crate(s) in the meantime. Offer"
                        " cancelled."
                    )
                )
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"-$1,'
                ' "money"="money"+$2 WHERE "user"=$3;',
                quantity,
                price,
                ctx.author.id,
            )
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1,'
                ' "money"="money"-$2 WHERE "user"=$3;',
                quantity,
                price,
                buyer.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=buyer.id,
                subject="crates",
                data={
                    "Quantity": quantity,
                    "Rarity": rarity,
                    "Price": price,
                },
                conn=conn,
            )
            await self.bot.log_transaction(
                ctx,
                from_=buyer.id,
                to=ctx.author.id,
                subject="money",
                data={
                    "Price": price,
                    "Quantity": quantity,
                    "Rarity": rarity,
                },
                conn=conn,
            )

        await self.bot.cache.update_profile_cols_rel(
            ctx.author.id, money=price, **{f"crates_{rarity}": -quantity}
        )
        await self.bot.cache.update_profile_cols_rel(
            buyer.id, money=-price, **{f"crates_{rarity}": quantity}
        )

        await ctx.send(
            _(
                "{buyer}, you've successfully bought **{quantity} {emoji} {rarity}**"
                " crate(s) from {seller}. Use `{prefix}crates` to view your updated"
                " crates."
            ).format(
                buyer=buyer.mention,
                quantity=quantity,
                emoji=getattr(self.emotes, rarity),
                rarity=rarity,
                seller=ctx.author.mention,
                prefix=ctx.prefix,
            )
        )


def setup(bot):
    bot.add_cog(Crates(bot))
