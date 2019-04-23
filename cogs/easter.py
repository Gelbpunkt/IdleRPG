"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import random

from discord.ext import commands

from utils.checks import has_char


class Easter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def easter(self, ctx):
        """Easter related commands for trading your collected eastereggs in for rewards."""
        await ctx.send(
            f"**Easter event <:easteregg:566251086986608650>**\n\nLasts until the Tuesday after Easter!\nCollect eastereggs and use `{ctx.prefix}easter rewards` to check the rewards. <:bunny:566290173831151627>\nHappy hunting!"
        )

    @has_char()
    @easter.command()
    async def rewards(self, ctx):
        """See the rewards for easter event."""
        await ctx.send(
            f"""
**Easter event - rewards**
Use `{ctx.prefix}easter reward [1-10]` to trade your eggs in.

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

You have **{ctx.character_data["eastereggs"]}** <:easteregg:566251086986608650>."""
        )

    @has_char()
    @easter.command()
    async def reward(self, ctx, reward_id: int):
        """Get your easter reward. ID may be 1 to 10."""
        if reward_id < 1 or reward_id > 10:
            return await ctx.send("Invalid reward.")
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
            return await ctx.send("You don't have enough eggs to claim this.")

        if reward[1] == "crates":
            await self.bot.pool.execute(
                'UPDATE profile SET "crates"="crates"+$1, "eastereggs"="eastereggs"-$2 WHERE "user"=$3;',
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
            type_ = random.choice(["Sword", "Shield"])
            atk = random.randint(reward[2], reward[3]) if type_ == "Sword" else 0.00
            deff = random.randint(reward[2], reward[3]) if type_ == "Shield" else 0.00
            name = (
                random.choice(["Bunny Ear", "Egg Cannon", "Chocolate Bar"])
                if type_ == "Sword"
                else random.choice(["Giant Egg", "Sweet Defender"])
            )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET "eastereggs"="eastereggs"-$1 WHERE "user"=$2;',
                    reward[0],
                    ctx.author.id,
                )
                id_ = await conn.fetchval(
                    'INSERT INTO allitems ("owner", "type", "armor", "damage", "name", "value") VALUES ($1, $2, $3, $4, $5, $6) RETURNING "id";',
                    ctx.author.id,
                    type_,
                    deff,
                    atk,
                    name,
                    100,
                )
                await conn.execute(
                    'INSERT INTO inventory ("equipped", "item") VALUES ($1, $2);',
                    False,
                    id_,
                )
        await ctx.send(
            "You claimed your reward. Check your inventory/boosters/crates/money/etc.! You can claim multiple rewards, keep hunting!"
        )


def setup(bot):
    bot.add_cog(Easter(bot))
