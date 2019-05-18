"""
The IdleRPG Discord Bot
Copyright (C) 2018-2019 Diniboy and Gelbpunkt

This software is dual-licensed under the GNU Affero General Public License for non-commercial and the Travitia License for commercial use.
For more information, see README.md and LICENSE.md.
"""
import asyncio
import math
import random

import discord
from discord.ext import commands

from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_money, user_has_char


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(1800)
    @commands.command()
    async def tournament(self, ctx, prize: IntFromTo(0, 100_000_000)):
        """Starts a new tournament."""
        if ctx.character_data["money"] < prize:
            return await ctx.send("You are too poor.")
        msg = await ctx.send(
            f"{ctx.author.mention} started a tournament! Free entries, prize is **${prize}**! React with \U00002694 to join!"
        )
        participants = [ctx.author]
        acceptingentries = True

        def simplecheck(r, u):
            return (
                r.message.id == msg.id
                and u not in participants
            )

        while acceptingentries:
            try:
                r, u = await self.bot.wait_for("reaction_add", timeout=30, check=simplecheck)
            except asyncio.TimeoutError:
                acceptingentries = False
                if len(participants) < 2:
                    return await ctx.send(
                        f"Noone joined your tournament, {ctx.author.mention}."
                    )
            if await user_has_money(self.bot, u.id, prize):
                participants.append(res.author)
                await ctx.send(f"{res.author.mention} joined the tournament.")
            else:
                await ctx.send(f"You don't have a character, {res.author.mention}.")
        toremove = 2 ** math.floor(math.log2(len(participants)))
        if toremove != len(participants):
            await ctx.send(
                f"There are **{len(participants)}** entries, due to the fact we need a playable tournament, the last **{len(participants) - toremove}** have been removed."
            )
            participants = participants[: -(len(participants) - toremove)]
        else:
            await ctx.send(f"Tournament started with **{toremove}** entries.")
        remain = participants
        while len(participants) > 1:
            random.shuffle(participants)
            matches = list(chunks(remain, 2))
            for match in matches:
                await ctx.send(f"{match[0].mention} vs {match[1].mention}")
                await asyncio.sleep(2)
                sw1, sh1 = await self.bot.get_equipped_items_for(match[0])
                sw2, sh2 = await self.bot.get_equipped_items_for(match[1])
                val1 = (sw1["damage"] if sw1 else 0) + (sh1["armor"] if sh1 else 0) + random.randint(1, 7)
                val2 = (sw2["damage"] if sw2 else 0) + (sh2["armor"] if sh2 else 0) + random.randint(1, 7)
                if val1 > val2:
                    winner = match[0]
                    looser = match[1]
                elif val2 > val1:
                    winner = match[1]
                    looser = match[0]
                else:
                    winner = random.choice(match)
                    looser = match[1 - match.index(winner)]
                participants.remove(looser)
                await ctx.send(f"Winner of this match is {winner.mention}!")
                await asyncio.sleep(2)

            await ctx.send("Round Done!")

        msg = await ctx.send(f"Tournament ended! The winner is {participants[0].mention}.")
        if not await has_money(self.bot, ctx.author.id, prize):
            return await ctx.send("The creator spent money, prize can't be given!")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                prize,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                prize,
                participants[0].id,
            )
        await msg.edit(
            content=f"Tournament ended! The winner is {participants[0].mention}.\nMoney was given!"
        )


def setup(bot):
    bot.add_cog(Tournament(bot))
