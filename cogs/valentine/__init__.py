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
import datetime
import random
import secrets

import discord

from discord.ext import commands

from cogs.shard_communication import next_day_cooldown
from utils.checks import has_char


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
        return secrets.choice(self.valentine_items[type_])

    @has_char()
    @next_day_cooldown()
    @commands.command()
    @locale_doc
    async def valentine(self, ctx):
        _("""Gift your spouse some boxes of chocolates""")
        today = datetime.datetime.now().day
        if today > 13 or today < 15:
            return await ctx.send(_("It's not time for that yet!"))
        if not ctx.character_data["marriage"]:
            return await ctx.send(_("You're not married yet."))

        await self.bot.pool.execute(
            'UPDATE profile SET "chocolates"="chocolates"+3 WHERE "user"=$1;',
            ctx.character_data["marriage"],
        )
        await ctx.send(_("You gave your spouse some boxes of chocolates :heart:"))
        user = await self.bot.get_user_global(ctx.character_data["marriage"])
        if user:
            await user.send(
                _(
                    "Your spouse gave you some boxes of chocolates :heart:\nYou can open it with {prefix}chocolate."
                ).format(prefix=ctx.prefix)
            )

    @has_char()
    @commands.command()
    @locale_doc
    async def chocolate(self, ctx):
        _("""Opens one of your chocolate boxes""")
        if ctx.character_data["chocolates"] <= 0:
            return await ctx.send(_("You have no chocolate boxes left."))
        await self.bot.pool.execute(
            'UPDATE profile SET "chocolates"="chocolates"-1 WHERE "user"=$1',
            ctx.author.id,
        )

        prize = random.choice(["money", "item", "lovescore", "lovescore"])
        if prize == "money":
            money = random.randint(1, 10) * 1000
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
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
            item = await self.bot.create_item(**item)
            embed = discord.Embed(
                title=_("You gained an item!"),
                description=_("The chocolate box contained an item!"),
                color=0xFF0000,
            )
            embed.set_thumbnail(url=ctx.author.avatar_url)
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
