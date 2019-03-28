"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""


import discord
import asyncio
import random

from discord.ext import commands
from utils.checks import has_char, has_money, user_has_char
from cogs.shard_communication import user_on_cooldown as user_cooldown


class Battles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(90)
    @commands.command(
        pass_context=True, description="Battle someone for the money you choose."
    )
    async def battle(self, ctx, money: int, enemy: discord.Member = None):
        if money < 0:
            return await ctx.send("Don't scam!")
        if enemy:
            if enemy.id == ctx.author.id:
                return await ctx.send("You can't battle yourself.")
        if not await has_money(self.bot, ctx.author.id, money):
            return await ctx.send("You are too poor.")

        if not enemy:
            await ctx.send(
                f"{ctx.author.mention} seeks a battle! Write `join @{str(ctx.author)}` now to duel him! The price is **${money}**."
            )
        else:
            await ctx.send(
                f"{ctx.author.mention} seeks a battle with {enemy.mention}! Write `private join @{str(ctx.author)}` now to duel him! The price is **${money}**."
            )

        seeking = True

        def allcheck(amsg):
            return (
                amsg.content.strip() == f"join <@{ctx.author.id}>"
                or amsg.content.strip() == f"join <@!{ctx.author.id}>"
            ) and amsg.author.id != ctx.author.id

        def privatecheck(amsg):
            return (
                amsg.content.strip() == f"private join <@{ctx.author.id}>"
                or amsg.content.strip() == f"private join <@!{ctx.author.id}>"
            ) and amsg.author.id == enemy.id

        try:
            while seeking:
                if enemy is None:
                    res = await self.bot.wait_for("message", timeout=60, check=allcheck)
                else:
                    res = await self.bot.wait_for(
                        "message", timeout=60, check=privatecheck
                    )
                if await has_money(self.bot, res.author.id, money):
                    seeking = False
                else:
                    await ctx.send("You don't have enough money to join the battle.")
        except asyncio.TimeoutError:
            return await ctx.send(
                f"Noone wanted to join your battle, {ctx.author.mention}. Try again later!"
            )

        await ctx.send(
            f"Battle **{ctx.message.author.name}** vs **{res.author.name}** started! 30 seconds of fighting will now start!"
        )
        PLAYERS = {ctx.author: 0, res.author: 0}
        async with self.bot.pool.acquire() as conn:
            for player in PLAYERS:
                sword = await conn.fetchval(
                    "SELECT ai.damage FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                    player.id,
                )
                if sword:
                    PLAYERS[player] += sword
                shield = await conn.fetchval(
                    "SELECT ai.armor FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                    player.id,
                )
                if shield:
                    PLAYERS[player] += shield
        for i in PLAYERS:
            PLAYERS[i] += random.randint(1, 7)
        ratings = list(PLAYERS.items())
        if ratings[0][1] > ratings[1][1]:
            winner = ratings[0][0]
            looser = ratings[1][0]
        elif ratings[0][1] < ratings[1][1]:
            winner = ratings[1][0]
            looser = ratings[0][0]
        else:
            winner = random.choice(ratings)
            looser = ratings[1 - ratings.index(winner)][0]
            winner = winner[0]
        await asyncio.sleep(30)
        if not await has_money(self.bot, winner.id, money) or not await has_money(
            self.bot, looser.id, money
        ):
            return await ctx.send(
                "One of you can't pay the price for the battle because he spent money in the time of fighting."
            )
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=$1;', winner.id
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, winner.id
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, looser.id
            )
        await ctx.send(
            f"{winner.mention} won the battle vs {looser.mention}! Congratulations!"
        )

    @has_char()
    @user_cooldown(90)
    @commands.command(description="Active Battles.")
    async def activebattle(self, ctx, money: int, enemy: discord.Member = None):
        if money < 0:
            return await ctx.send("Don't scam!")
        if enemy:
            if enemy.id == ctx.author.id:
                return await ctx.send("You can't battle yourself.")
        if not await has_money(self.bot, ctx.author.id, money):
            return await ctx.send("You are too poor.")
        if not enemy:
            await ctx.send(
                f"{ctx.author.mention} seeks an active battle! Write `active join @{str(ctx.author)}` now to duel him! The price is **${money}**."
            )
        else:
            await ctx.send(
                f"{ctx.author.mention} seeks an active battle with {enemy.mention}! Write `active private join @{str(ctx.author)}` now to duel him! The price is **${money}**."
            )

        def allcheck(amsg):
            return (
                amsg.content.strip() == f"active join <@{ctx.author.id}>"
                or amsg.content.strip() == f"active join <@!{ctx.author.id}>"
            ) and amsg.author.id != ctx.author.id

        def privatecheck(amsg):
            return (
                amsg.content.strip() == f"active private join <@{ctx.author.id}>"
                or amsg.content.strip() == f"active private join <@!{ctx.author.id}>"
            ) and amsg.author.id == enemy.id

        try:
            if not enemy:
                res = await self.bot.wait_for("message", timeout=60, check=allcheck)
            else:
                res = await self.bot.wait_for("message", timeout=60, check=privatecheck)
        except asyncio.TimeoutError:
            return await ctx.send(
                f"Noone wanted to join your battle, {ctx.author.mention}. Try again later!"
            )

        if not await user_has_char(self.bot, res.author.id):
            return await ctx.send(
                f"You don't have a character yet. Use `{ctx.prefix}create` to start!"
            )

        if not await has_money(self.bot, res.author.id, money):
            return await ctx.send("The enemy who joined is too poor. Battle cancelled.")

        PLAYERS = [ctx.author, res.author]
        HP = []

        DAMAGE = []
        ARMOR = []

        async with self.bot.pool.acquire() as conn:
            for p in PLAYERS:
                c = await conn.fetchval(
                    'SELECT class FROM profile WHERE "user"=$1;', p.id
                )
                if c in ["Caretaker", "Trainer", "Bowman", "Hunter", "Ranger"]:
                    HP.append(120)
                else:
                    HP.append(100)

                d = await conn.fetchval(
                    "SELECT ai.damage FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                    p.id,
                )
                DAMAGE.append(d or 0.00)
                a = await conn.fetchval(
                    "SELECT ai.armor FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                    p.id,
                )
                ARMOR.append(a or 0.00)

        for i in range(2):
            ARMOR[i] = int(ARMOR[i])
            DAMAGE[i] = int(DAMAGE[i])

        def is_valid_move(msg):
            return (
                msg.content.lower() in ["attack", "defend", "recover"]
                and msg.author in PLAYERS
            )

        while HP[0] > 0 and HP[1] > 0:
            await ctx.send(
                f"{PLAYERS[0].mention}: **{HP[0]}** HP\n{PLAYERS[1].mention}: **{HP[1]}** HP\nUse `attack`, `defend` or `recover`."
            )
            MOVES_DONE = {}
            while len(MOVES_DONE) < 2:
                try:
                    res = await self.bot.wait_for(
                        "message", timeout=30, check=is_valid_move
                    )
                except asyncio.TimeoutError:
                    return await ctx.send("Someone refused to move. Battle stopped.")
                if res.author not in MOVES_DONE.keys():
                    MOVES_DONE[res.author] = res.content.lower()
                else:
                    await ctx.send(f"{res.author.mention}, you already moved!")
            plz = list(MOVES_DONE.keys())
            for u in plz:
                o = plz[:]
                o = o[1 - plz.index(u)]
                idx = PLAYERS.index(u)
                if MOVES_DONE[u] == "recover":
                    HP[idx] += 20
                    await ctx.send(f"{u.mention} healed himself for **20 HP**.")
                elif MOVES_DONE[u] == "attack" and MOVES_DONE[o] != "defend":
                    eff = random.choice(
                        [
                            int(DAMAGE[idx]),
                            int(DAMAGE[idx] * 0.5),
                            int(DAMAGE[idx] * 0.2),
                            int(DAMAGE[idx] * 0.8),
                        ]
                    )
                    HP[1 - idx] -= eff
                    await ctx.send(f"{u.mention} hit {o.mention} for **{eff}** damage.")
                elif MOVES_DONE[u] == "attack" and MOVES_DONE[o] == "defend":
                    eff = random.choice(
                        [
                            int(DAMAGE[idx]),
                            int(DAMAGE[idx] * 0.5),
                            int(DAMAGE[idx] * 0.2),
                            int(DAMAGE[idx] * 0.8),
                        ]
                    )
                    eff2 = random.choice(
                        [
                            int(ARMOR[idx]),
                            int(ARMOR[idx] * 0.5),
                            int(ARMOR[idx] * 0.2),
                            int(ARMOR[idx] * 0.8),
                        ]
                    )
                    if eff - eff2 > 0:
                        HP[1 - idx] -= eff - eff2
                        await ctx.send(
                            f"{u.mention} hit {o.mention} for **{eff-eff2}** damage."
                        )
                    else:
                        await ctx.send(f"{u.mention}'s attack on {o.mention} failed!")
        if HP[0] <= 0 and HP[1] <= 0:
            return await ctx.send("You both died!")
        idx = HP.index([h for h in HP if h <= 0][0])
        winner = PLAYERS[1 - idx]
        looser = PLAYERS[idx]
        if not await has_money(self.bot, winner.id, money) or not await has_money(
            self.bot, looser.id, money
        ):
            return await ctx.send(
                "One of you both can't pay the price for the battle because he spent money in the time of fighting."
            )
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=$1;', winner.id
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;', money, winner.id
            )
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;', money, looser.id
            )
        await ctx.send(
            f"{winner.mention} won the active battle vs {looser.mention}! Congratulations!"
        )


def setup(bot):
    bot.add_cog(Battles(bot))
