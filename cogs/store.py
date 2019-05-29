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
import discord
from discord.ext import commands

from classes.converters import IntGreaterThan
from utils.checks import has_char


class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @locale_doc
    async def store(self, ctx):
        _("""The booster store.""")
        shopembed = discord.Embed(
            title=_("IdleRPG Store"),
            description=_(
                "Welcome! Use `{prefix}purchase time/luck/money` to buy something."
            ).format(prefix=ctx.prefix),
            colour=discord.Colour.blurple(),
        )
        shopembed.add_field(
            name=_("Boosters"),
            value=_(
                "`#1` Time Booster\t**$1000**\tBoosts adventure time by 50%\n`#2` Luck Booster\t**$500**\tBoosts adventure luck by 25%\n`#3` Money Booster\t**$1000**\tBoosts adventure money rewards by 25%"
            ),
            inline=False,
        )
        shopembed.set_thumbnail(url=f"{self.bot.BASE_URL}/business.png")
        await ctx.send(embed=shopembed)

    @has_char()
    @commands.command()
    @locale_doc
    async def purchase(self, ctx, booster: str.lower, amount: IntGreaterThan(0) = 1):
        _("""Buy a booster from the store.""")
        if booster not in ["time", "luck", "money"]:
            return await ctx.send(_("Please either buy `time`, `luck` or `money`."))
        price = {"time": 1000, "luck": 500, "money": 1000}[booster] * amount
        if ctx.character_data["money"] < price:
            return await ctx.send(_("You're too poor."))
        await self.bot.pool.execute(
            f'UPDATE profile SET {booster}_booster={booster}_booster+$1, "money"="money"-$2 WHERE "user"=$3;',
            amount,
            price,
            ctx.author.id,
        )
        await ctx.send(
            _(
                "Successfully bought **{amount}** {booster} booster(s). Use `{prefix}boosters` to view your new boosters."
            ).format(amount=amount, booster=booster.title(), prefix=ctx.prefix)
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def boosters(self, ctx):
        _("""View your boosters.""")
        timeboosters = ctx.character_data["time_booster"]
        luckboosters = ctx.character_data["luck_booster"]
        moneyboosters = ctx.character_data["money_booster"]
        time = await self.bot.get_booster(ctx.author, "time")
        luck = await self.bot.get_booster(ctx.author, "luck")
        money = await self.bot.get_booster(ctx.author, "money")
        time = (
            _("Time booster - {time}").format(time=str(time).split(".")[0])
            if time
            else None
        )
        luck = (
            _("Luck booster - {time}").format(time=str(luck).split(".")[0])
            if luck
            else None
        )
        money = (
            _("Money booster - {time}").format(time=str(money).split(".")[0])
            if money
            else None
        )
        actives = "\n".join([b for b in [time, luck, money] if b])
        text = _("Currently active")
        if time or luck or money:
            desc = f"**{text}**\n{actives}"
        else:
            desc = ""
        a, b, c = _("Time Boosters"), _("Luck Boosters"), _("Money Boosters")
        await ctx.send(
            embed=discord.Embed(
                title=_("Your Boosters"),
                description=f"{desc}\n\n{a}: `{timeboosters}`\n{b}: `{luckboosters}`\n{c}: `{moneyboosters}`",
                colour=discord.Colour.blurple(),
            ).set_footer(
                text=_("Use {prefix}activate to activate one").format(prefix=ctx.prefix)
            )
        )

    @has_char()
    @commands.command()
    @locale_doc
    async def activate(self, ctx, boostertype: str.lower):
        _("""Activate a booster.""")
        if boostertype not in ["time", "luck", "money"]:
            return await ctx.send(
                _("That is not a valid booster type. Must be `time/luck/money`.")
            )
        boosters = ctx.character_data[f"{boostertype}_booster"]
        if not boosters:
            return await ctx.send(_("You don't have any of these boosters."))
        check = await self.bot.get_booster(ctx.author, boostertype)
        if check:
            return await ctx.send(_("This booster is already running."))
        await self.bot.pool.execute(
            f'UPDATE profile SET "{boostertype}_booster"="{boostertype}_booster"-1 WHERE "user"=$1;',
            ctx.author.id,
        )
        await self.bot.activate_booster(ctx.author, boostertype)
        await ctx.send(
            _(
                "Successfully activated a **{booster} booster** for the next **24 hours**!"
            ).format(booster=booster.title())
        )


def setup(bot):
    bot.add_cog(Store(bot))
