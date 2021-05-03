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
import datetime

import discord

from discord.ext import commands

from cogs.shard_communication import next_day_cooldown
from utils import random
from utils.checks import has_char
from utils.i18n import _, locale_doc


class Valentine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.valentine_items = {
            "Sword": ["Blade of Affection"],
            "Shield": ["Love Shield", "Letter of Love"],
            "Axe": ["Kiss Kiss Chop Chop"],
            "Scythe": ["'Til Death do us part", "Blade of Cuteness"],
            "Bow": ["Cupid's Bow", "Lovestruck Crossbow"],
            "Howlet": ["Lovebird"],
            "Spear": ["Distant Kisses"],
            "Wand": ["Mindbender"],
            "Knife": ["Close Combat Kisses"],
            "Dagger": ["Thieve's Heart"],
            "Hammer": ["Heartfelt Bonk"],
        }

    def get_valentine_name(self, type_):
        return random.choice(self.valentine_items[type_])

    @has_char()
    @next_day_cooldown()
    @commands.command(brief=_("Gift your partner some chocolate boxes"))
    @locale_doc
    async def valentine(self, ctx):
        _(
            """Gift your spouse three boxes of chocolates, they can contain lovescore, money or valentine's themed items.

            Your spouse may open the boxes with `{prefix}chocolate`.

            Only players who are married may use this command.
            This command may only be used from the 13th to the 15th February.
            (This command has a cooldown until 12am UTC.)"""
        )
        today = datetime.datetime.now().day
        if not 13 <= today <= 15:
            return await ctx.send(_("It's not time for that yet!"))
        if not ctx.character_data["marriage"]:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You're not married yet."))

        await self.bot.pool.execute(
            'UPDATE profile SET "chocolates"="chocolates"+3 WHERE "user"=$1;',
            ctx.character_data["marriage"],
        )
        await self.bot.cache.update_profile_cols_rel(
            ctx.character_data["marriage"], chocolates=3
        )
        await ctx.send(_("You gave your spouse some boxes of chocolates :heart:"))
        user = await self.bot.get_user_global(ctx.character_data["marriage"])
        if user:
            await user.send(
                "Your spouse gave you some boxes of chocolates :heart:\nYou can open it"
                " with $chocolate."
            )

    @has_char()
    @commands.command(brief=_("Open one of your chocolate boxes"))
    @locale_doc
    async def chocolate(self, ctx):
        _(
            """Opens one of your chocolate boxes.
            These boxes have a 1/4 chance of containing money, a 1/4 chance for an item and a 2/4 chance for lovescore."""
        )
        if ctx.character_data["chocolates"] <= 0:
            return await ctx.send(_("You have no chocolate boxes left."))
        await self.bot.pool.execute(
            'UPDATE profile SET "chocolates"="chocolates"-1 WHERE "user"=$1',
            ctx.author.id,
        )
        await self.bot.cache.update_profile_cols_rel(ctx.author.id, chocolates=-1)

        prize = random.choice(["money", "item", "lovescore", "lovescore"])
        if prize == "money":
            money = random.randint(1, 10) * 1000
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": money},
                    conn=conn,
                )
            await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=money)
            return await ctx.send(
                _("The chocolate box contained **${money}!**").format(money=money)
            )
        elif prize == "lovescore":
            lovescore = random.randint(5, 10) * 1000
            await self.bot.pool.execute(
                'UPDATE profile SET "lovescore"="lovescore"+$1 WHERE "user"=$2;',
                lovescore,
                ctx.author.id,
            )
            await self.bot.cache.update_profile_cols_rel(
                ctx.author.id, lovescore=lovescore
            )
            return await ctx.send(
                _(
                    "The chocolate box contained **{lovescore} lovescore points!**"
                ).format(lovescore=lovescore)
            )
        else:
            minstat = round(ctx.character_data["lovescore"] / 250_000) or 1
            maxstat = round(ctx.character_data["lovescore"] / 100_000) or 1

            item = await self.bot.create_random_item(
                minstat=minstat if minstat < 30 else 30,
                maxstat=maxstat if maxstat < 30 else 30,
                minvalue=1,
                maxvalue=250,
                owner=ctx.author,
                insert=False,
            )
            item["name"] = self.get_valentine_name(item["type_"])

            async with self.bot.pool.acquire() as conn:
                item = await self.bot.create_item(**item, conn=conn)
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="item",
                    data={"Name": item["name"], "Value": item["value"]},
                    conn=conn,
                )
            embed = discord.Embed(
                title=_("You gained an item!"),
                description=_("The chocolate box contained an item!"),
                color=0xff0000,
            )
            embed.set_thumbnail(url=ctx.author.avatar.url)
            embed.add_field(name=_("ID"), value=item["id"], inline=False)
            embed.add_field(name=_("Name"), value=item["name"], inline=False)
            embed.add_field(name=_("Type"), value=item["type"], inline=False)
            if item["type"] == "Shield":
                embed.add_field(name=_("Armor"), value=item["armor"], inline=True)
            else:
                embed.add_field(name=_("Damage"), value=item["damage"], inline=True)
            embed.add_field(name=_("Value"), value=f"${item['value']}", inline=False)
            embed.set_footer(
                text=_("You have {chocolates} left").format(
                    chocolates=ctx.character_data["chocolates"] - 1
                )
            )
            return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Valentine(bot))
