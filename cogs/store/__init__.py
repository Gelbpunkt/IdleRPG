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
import discord

from discord.ext import commands

from classes.converters import IntGreaterThan
from utils.checks import has_char
from utils.i18n import _, locale_doc


class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=_("Show the booster store"))
    @locale_doc
    async def store(self, ctx):
        _(
            """Show the booster store. For a detailed explanation what the boosters do, check `{prefix}help boosters`."""
        )
        shopembed = discord.Embed(
            title=_("IdleRPG Store"),
            description=_(
                "Welcome! Use `{prefix}purchase time/luck/money` to buy something."
            ).format(prefix=ctx.clean_prefix),
            colour=discord.Colour.blurple(),
        )
        shopembed.add_field(
            name=_("Boosters"),
            value=_(
                "`#1` Time Booster\t**$1000**\tBoosts adventure time by 50%\n`#2` Luck"
                " Booster\t**$500**\tBoosts adventure luck (not `{prefix}luck`) by"
                " 25%\n`#3` Money Booster\t**$1000**\tBoosts adventure money rewards"
                " by 25%"
            ).format(prefix=ctx.clean_prefix),
            inline=False,
        )
        shopembed.set_thumbnail(url=f"{self.bot.BASE_URL}/business.png")
        await ctx.send(embed=shopembed)

    @has_char()
    @commands.command(brief=_("Buy some boosters"))
    @locale_doc
    async def purchase(self, ctx, booster: str.lower, amount: IntGreaterThan(0) = 1):
        _(
            """`<booster>` - The booster type to buy, can be time, luck, money or all
            `[amount]` - The amount of boosters to buy; defaults to 1

            Buy one or more booster from the store. For a detailed explanation what the boosters do, check `{prefix}help boosters`."""
        )
        if booster not in ["time", "luck", "money", "all"]:
            return await ctx.send(_("Please either buy `time`, `luck` or `money`."))
        price = {"time": 1000, "luck": 500, "money": 1000, "all": 2500}[
            booster
        ] * amount
        if ctx.character_data["money"] < price:
            return await ctx.send(_("You're too poor."))
        if booster != "all":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    f"UPDATE profile SET {booster}_booster={booster}_booster+$1,"
                    ' "money"="money"-$2 WHERE "user"=$3;',
                    amount,
                    price,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": price},
                    conn=conn,
                )
        else:
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "time_booster"="time_booster"+$1,'
                    ' "luck_booster"="luck_booster"+$1,'
                    ' "money_booster"="money_booster"+$1, "money"="money"-$2 WHERE'
                    ' "user"=$3;',
                    amount,
                    price,
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=ctx.author.id,
                    to=2,
                    subject="money",
                    data={"Amount": price},
                    conn=conn,
                )
        await ctx.send(
            _(
                "Successfully bought **{amount}x** {booster} booster(s). Use"
                " `{prefix}boosters` to view your new boosters."
            ).format(amount=amount, booster=booster, prefix=ctx.clean_prefix)
        )

    @has_char()
    @commands.command(aliases=["b"], brief=_("View your boosters"))
    @locale_doc
    async def boosters(self, ctx):
        _(
            """View your boosters and the active ones' status. Each one has a different effect.

              - Time boosters halve the adventures' times (must be active before starting an adventure)
              - Luck boosters increase your adventure chances by 25%
              - Money boosters increase the amount of gold gained from adventures by 25%

            Each booster lasts 24 hours after activation."""
        )
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
                description=(
                    f"{desc}\n\n{a}: `{timeboosters}`\n{b}: `{luckboosters}`\n{c}:"
                    f" `{moneyboosters}`"
                ),
                colour=discord.Colour.blurple(),
            ).set_footer(
                text=_("Use {prefix}activate to activate one").format(prefix=ctx.clean_prefix)
            )
        )

    @has_char()
    @commands.command(brief=_("Activate a booster"))
    @locale_doc
    async def activate(self, ctx, boostertype: str.lower):
        _(
            """`<boostertype>` - The booster type to activate, can be time, luck, money or all

            Activate a booster. For a detailed explanation what the boosters do, check `{prefix}help boosters`."""
        )
        if boostertype not in ["time", "luck", "money", "all"]:
            return await ctx.send(
                _("That is not a valid booster type. Must be `time/luck/money/all`.")
            )
        if boostertype != "all":
            boosters = ctx.character_data[f"{boostertype}_booster"]
            if boosters <= 0:
                return await ctx.send(_("You don't have any of these boosters."))
            check = await self.bot.get_booster(ctx.author, boostertype)
            if check:
                if not await ctx.confirm(
                    _(
                        "This booster is already running. Do you want to refresh it"
                        " anyways?"
                    )
                ):
                    return

            await self.bot.pool.execute(
                f'UPDATE profile SET "{boostertype}_booster"="{boostertype}_booster"-1'
                ' WHERE "user"=$1;',
                ctx.author.id,
            )
            await self.bot.activate_booster(ctx.author, boostertype)
            await ctx.send(
                _(
                    "Successfully activated a **{booster} booster** for the next **24"
                    " hours**!"
                ).format(booster=boostertype.title())
            )
        else:
            if not await ctx.confirm(
                _(
                    "This will overwrite all active boosters and refresh them. Are you"
                    " sure?"
                )
            ):
                return

            reducible = [
                i
                for i in ("time", "luck", "money")
                if ctx.character_data[f"{i}_booster"]
            ]

            if not reducible:
                return await ctx.send(_("Nothing to activate."))

            to_reduce = ", ".join([f'"{i}_booster"="{i}_booster"-1' for i in reducible])

            await self.bot.pool.execute(
                f'UPDATE profile SET {to_reduce} WHERE "user"=$1;', ctx.author.id
            )

            for i in reducible:
                await self.bot.activate_booster(ctx.author, i)
            await ctx.send(
                _("Successfully activated {types} for the next **24 hours**!").format(
                    types=", ".join(reducible)
                )
            )


async def setup(bot):
    await bot.add_cog(Store(bot))
