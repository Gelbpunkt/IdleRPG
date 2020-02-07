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
import random

from discord.ext import commands

from classes.converters import IntFromTo
from utils.checks import has_char


class Easter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @locale_doc
    async def easter(self, ctx):
        _(
            """Easter related commands for trading your collected eastereggs in for rewards."""
        )
        await ctx.send(
            _(
                "**Easter event <:easteregg:566251086986608650>**\n\nLasts until the Tuesday after Easter!\nCollect eastereggs and use `{prefix}easter rewards` to check the rewards. <:bunny:566290173831151627>\nHappy hunting!"
            ).format(prefix=ctx.prefix)
        )

    @has_char()
    @easter.command()
    @locale_doc
    async def rewards(self, ctx):
        _("""See the rewards for easter event.""")
        await ctx.send(
            _(
                """
**Easter event - rewards**
Use `{prefix}easter reward [1-10]` to trade your eggs in.

**100 <:easteregg:566251086986608650>** - 1 crate
**500 <:easteregg:566251086986608650>** - $10000
**1000 <:easteregg:566251086986608650>** - random item 1-49
**2000 <:easteregg:566251086986608650>** - 25 crates
**2500 <:easteregg:566251086986608650>** - 10 boosters of each type
**5000 <:easteregg:566251086986608650>** - 100 crates
**7500 <:easteregg:566251086986608650>** - easter guild badge
**7500 <:easteregg:566251086986608650>** - 200 crates
**7500 <:easteregg:566251086986608650>** - random item 40-50
**10000 <:easteregg:566251086986608650>** - random 50 stat item

You have **{eggs}** <:easteregg:566251086986608650>."""
            ).format(prefix=ctx.prefix, eggs=ctx.character_data["eastereggs"])
        )

    @has_char()
    @easter.command()
    @locale_doc
    async def reward(self, ctx, reward_id: IntFromTo(1, 10)):
        _("""Get your easter reward. ID may be 1 to 10.""")
        reward = [
            (100, "crates", 1),
            (500, "money", 10000),
            (1000, "item", 1, 49),
            (2000, "crates", 25),
            (2500, "boosters", 10),
            (5000, "crates", 100),
            (7500, "badge"),
            (7500, "crates", 200),
            (7500, "item", 40, 50),
            (10000, "item", 50, 50),
        ][reward_id - 1]
        if ctx.character_data["eastereggs"] < reward[0]:
            return await ctx.send(_("You don't have enough eggs to claim this."))

        if reward[1] == "crates":
            await self.bot.pool.execute(
                'UPDATE profile SET "crates_common"="crates_common"+$1, "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
                reward[2],
                reward[0],
                ctx.author.id,
            )
        elif reward[1] == "money":
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1, "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
                reward[2],
                reward[0],
                ctx.author.id,
            )
        elif reward[1] == "boosters":
            await self.bot.pool.execute(
                'UPDATE profile SET "money_booster"="money_booster"+$1, "time_booster"="time_booster"+$1, "luck_booster"="luck_booster"+$1, "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
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
                    'UPDATE guilds SET "badges"=array_append("badges", $1) WHERE "id"=$2;',
                    "https://i.imgur.com/LOM8JcY.png",
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
            await self.bot.create_item(**item)
            await self.bot.pool.execute(
                'UPDATE profile SET "eastereggs"="eastereggs"-$1 WHERE "user"=$2;',
                reward[0],
                ctx.author.id,
            )
        await ctx.send(
            _(
                "You claimed your reward. Check your inventory/boosters/crates/money/etc.! You can claim multiple rewards, keep hunting!"
            )
        )


def setup(bot):
    bot.add_cog(Easter(bot))
