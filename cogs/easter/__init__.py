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
from discord.ext import commands

from classes.converters import IntFromTo
from utils import random
from utils.checks import has_char
from utils.i18n import _, locale_doc


class Easter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, brief=_("Easter related commands"))
    @locale_doc
    async def easter(self, ctx):
        _(
            """Contains all easter related commands. See `{prefix}help easter` for a list of commands.

            During the easter event, users will find eastereggs when finishing adventures, which can be exchanged for several rewards, including crates, items, money, or special guild badges."""
        )
        await ctx.send(
            _(
                "**Easter event <:easteregg:566251086986608650>**\n\nPart of Idle's"
                " birthday!\nCollect eastereggs and use `{prefix}easter rewards` to"
                " check the rewards. <:bunny:566290173831151627>\nHappy hunting!"
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @easter.command(brief=_("Lists all easter rewards"))
    @locale_doc
    async def rewards(self, ctx):
        _(
            """Shows all rewards available in the easter event, along with the reward ID.

            To claim a reward, use `{prefix}easter reward <ID>`."""
        )
        await ctx.send(
            _(
                """
**Easter event - rewards**
Use `{prefix}easter reward [1-9]` to trade your eggs in.

**(1) 100 <:easteregg:566251086986608650>** - 10 common crates
**(2) 500 <:easteregg:566251086986608650>** - $10000
**(3) 1000 <:easteregg:566251086986608650>** - random item 1-49
**(4) 2000 <:easteregg:566251086986608650>** - 250 common crates
**(5) 2500 <:easteregg:566251086986608650>** - 10 boosters of each type
**(6) 5000 <:easteregg:566251086986608650>** - 10 rare crates
**(7) 7500 <:easteregg:566251086986608650>** - birthday guild badge
**(8) 7500 <:easteregg:566251086986608650>** - 1 magic crate
**(9) 12500 <:easteregg:566251086986608650>** - 1 legendary crate
You have **{eggs}** <:easteregg:566251086986608650>."""
            ).format(prefix=ctx.prefix, eggs=ctx.character_data["eastereggs"])
        )

    @has_char()
    @easter.command(brief=_("Claim an easter reward"))
    @locale_doc
    async def reward(self, ctx, reward_id: IntFromTo(1, 9)):
        _(
            """`<reward_id>` - A whole number from 1 to 9

            Claim a reward by its ID.

            A list of rewards along with their ID can be seen with `{prefix}easter rewards`."""
        )
        reward = [
            (100, "crates", 10, "common"),
            (500, "money", 10000),
            (1000, "item", 1, 49),
            (2000, "crates", 250, "common"),
            (2500, "boosters", 10),
            (5000, "crates", 10, "rare"),
            (7500, "badge"),
            (7500, "crates", 1, "magic"),
            (12500, "crates", 1, "legendary"),
        ][reward_id - 1]
        if ctx.character_data["eastereggs"] < reward[0]:
            return await ctx.send(_("You don't have enough eggs to claim this."))

        if reward[1] == "crates":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    f'UPDATE profile SET "crates_{reward[3]}"="crates_{reward[3]}"+$1,'
                    ' "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
                    reward[2],
                    reward[0],
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="crates",
                    data={"Rarity": reward[3], "Amount": reward[2]},
                    conn=conn,
                )
        elif reward[1] == "money":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1,'
                    ' "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
                    reward[2],
                    reward[0],
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": reward[2]},
                    conn=conn,
                )
        elif reward[1] == "boosters":
            await self.bot.pool.execute(
                'UPDATE profile SET "money_booster"="money_booster"+$1,'
                ' "time_booster"="time_booster"+$1, "luck_booster"="luck_booster"+$1,'
                ' "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
                reward[2],
                reward[0],
                ctx.author.id,
            )
        elif reward[1] == "badge":
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "eastereggs"="eastereggs"-$1 WHERE "user"=$2;',
                    reward[0],
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE guild SET "badges"=array_append("badges", $1) WHERE'
                    ' "id"=$2;',
                    "https://idlerpg.xyz/image/birthday2021_badge.png",
                    ctx.character_data["guild"],
                )
        elif reward[1] == "item":
            item = await self.bot.create_random_item(
                minstat=reward[2],
                maxstat=reward[3],
                minvalue=1000,
                maxvalue=1000,
                owner=ctx.author,
                insert=False,
            )
            item["name"] = (
                random.choice(["Bunny Ear", "Egg Cannon", "Chocolate Bar"])
                if item["type_"] != "Shield"
                else random.choice(["Giant Egg", "Sweet Defender"])
            )
            async with self.bot.pool.acquire() as conn:
                await self.bot.create_item(**item, conn=conn)
                await conn.execute(
                    'UPDATE profile SET "eastereggs"="eastereggs"-$1 WHERE "user"=$2;',
                    reward[0],
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="item",
                    data={"Name": item["name"], "Value": item["value"]},
                    conn=conn,
                )

        await ctx.send(
            _(
                "You claimed your reward. Check your"
                " inventory/boosters/crates/money/etc.! You can claim multiple rewards,"
                " keep hunting!"
            )
        )


async def setup(bot):
    await bot.add_cog(Easter(bot))
