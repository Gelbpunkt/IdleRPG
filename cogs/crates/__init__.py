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
import random

from collections import namedtuple

import discord

from discord.ext import commands

from classes.converters import IntGreaterThan, MemberWithCharacter
from utils.checks import has_char


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
    @commands.command(aliases=["boxes"])
    @locale_doc
    async def crates(self, ctx):
        _("""Shows your crates.""")
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

    @has_char()
    @commands.command(name="open")
    @locale_doc
    async def _open(self, ctx, rarity: str.lower = "common"):
        _("""Opens a crate.""")
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        if ctx.character_data[f"crates_{rarity}"] < 1:
            return await ctx.send(
                _(
                    "Seems like you don't have any crate of this rarity yet. Vote me up to get a random one or find them!"
                )
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

        item = await self.bot.create_random_item(
            minstat=minstat, maxstat=maxstat, minvalue=1, maxvalue=250, owner=ctx.author
        )
        await self.bot.pool.execute(
            f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"-1 WHERE "user"=$1;',
            ctx.author.id,
        )
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
                f"**{ctx.author}** opened a legendary crate and \
received {item['name']} with **{item['damage'] or item['armor']} \
{'damage' if item['damage'] else 'armor'}**."
            )

    @has_char()
    @commands.command()
    @locale_doc
    async def tradecrate(
        self,
        ctx,
        other: MemberWithCharacter,
        amount: IntGreaterThan(0) = 1,
        rarity: str.lower = "common",
    ):
        _("""Trades crates to a user.""")
        if other == ctx.author:
            return await ctx.send(_("Very funny..."))
        if rarity not in ["common", "uncommon", "rare", "magic", "legendary"]:
            return await ctx.send(
                _("{rarity} is not a valid rarity.").format(rarity=rarity)
            )
        if ctx.character_data[f"crates_{rarity}"] < amount:
            return await ctx.send(_("You don't have any crates of this rarity."))
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"-$1 WHERE "user"=$2;',
                amount,
                ctx.author.id,
            )
            await conn.execute(
                f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE "user"=$2;',
                amount,
                other.id,
            )
        await ctx.send(
            _("Successfully gave {amount} {rarity} crate(s) to {other}.").format(
                amount=amount, other=other.mention, rarity=rarity
            )
        )
        await self.bot.log_transaction(
            ctx, from_=ctx.author, to=other, subject="crates", data=[amount, rarity]
        )


def setup(bot):
    bot.add_cog(Crates(bot))
