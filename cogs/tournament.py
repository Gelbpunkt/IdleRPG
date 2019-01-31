import discord
from discord.ext import commands
from cogs.help import chunks
import math
import random
import asyncio
from utils.checks import has_char, has_money, user_has_char

from cogs.shard_communication import user_on_cooldown as user_cooldown


def is_battle_owner():
    def predicate(ctx):
        member = ctx.bot.get_guild(430_017_996_304_678_923).get_member(
            ctx.author.id
        )  # cross server stuff
        if not member:
            return False
        return discord.utils.get(member.roles, name="Battle Owner") is not None

    return commands.check(predicate)


class Tournament:
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(1800)
    @commands.command(description="Start a new tournament with unlimited participants.")
    async def tournament(self, ctx, prize: int):
        if prize < 0 or prize > 100_000_000:
            return await ctx.send("Don't scam!")
        if not await has_money(self.bot, ctx.author.id, prize):
            return await ctx.send("You are too poor.")
        await ctx.send(
            f"{ctx.author.mention} started a tournament! Free entries, prize is **${prize}**! Type `tournament join @{ctx.author}` to join!"
        )
        participants = [ctx.author]
        acceptingentries = True

        def simplecheck(msg):
            return (
                (
                    msg.content.strip().lower() == f"tournament join <@{ctx.author.id}>"
                    or msg.content.strip().lower()
                    == f"tournament join <@!{ctx.author.id}>"
                )
                and msg.author != ctx.author
                and msg.author not in participants
            )

        while acceptingentries:
            try:
                res = await self.bot.wait_for("message", timeout=30, check=simplecheck)
                if await user_has_char(self.bot, res.author.id):
                    participants.append(res.author)
                    await ctx.send(f"{res.author.mention} joined the tournament.")
                else:
                    await ctx.send(f"You don't have a character, {res.author.mention}.")
                    continue
            except asyncio.TimeoutError:
                acceptingentries = False
                if len(participants) < 2:
                    return await ctx.send(
                        f"Noone joined your tournament, {ctx.author.mention}."
                    )
        toremove = 2 ** math.floor(math.log2(len(participants)))
        if toremove != len(participants):
            await ctx.send(
                f"There are **{len(participants)}** entries, due to the fact we need a playable tournament, the last **{len(participants) - toremove}** have been removed."
            )
            participants = participants[: -(len(participants) - toremove)]
        else:
            await ctx.send(f"Tournament started with **{toremove}** entries.")
        remain = participants
        while len(remain) > 1:
            random.shuffle(remain)
            matches = list(chunks(remain, 2))
            for match in matches:
                await ctx.send(f"{match[0].mention} vs {match[1].mention}")
                await asyncio.sleep(2)
                async with self.bot.pool.acquire() as conn:
                    sword1 = await conn.fetchrow(
                        "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                        match[0].id,
                    )
                    try:
                        sw1 = sword1["damage"]
                    except KeyError:
                        sw1 = 0
                    shield1 = await conn.fetchrow(
                        "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                        match[0].id,
                    )
                    try:
                        sh1 = shield1["armor"]
                    except KeyError:
                        sh1 = 0
                    sword2 = await conn.fetchrow(
                        "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Sword';",
                        match[1].id,
                    )
                    try:
                        sw2 = sword2["damage"]
                    except KeyError:
                        sw2 = 0
                    shield2 = await conn.fetchrow(
                        "SELECT ai.* FROM profile p JOIN allitems ai ON (p.user=ai.owner) JOIN inventory i ON (ai.id=i.item) WHERE i.equipped IS TRUE AND p.user=$1 AND type='Shield';",
                        match[1].id,
                    )
                    try:
                        sh2 = shield2["armor"]
                    except KeyError:
                        sh2 = 0
                val1 = sw1 + sh1 + random.randint(1, 7)
                val2 = sw2 + sh2 + random.randint(1, 7)
                if val1 > val2:
                    winner = match[0]
                    looser = match[1]
                elif val2 > val1:
                    winner = match[1]
                    looser = match[0]
                else:
                    winner = random.choice(match)
                    looser = match[1 - match.index(winner)]
                try:
                    remain.remove(looser)
                except ValueError:
                    pass  # for future happenings
                await ctx.send(f"Winner of this match is {winner.mention}!")
                await asyncio.sleep(2)

            await ctx.send("Round Done!")
        msg = await ctx.send(f"Tournament ended! The winner is {remain[0].mention}.")
        if not await has_money(self.bot, ctx.author.id, prize):
            return await ctx.send("The creator spent money, noone received one!")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                prize,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                prize,
                remain[0].id,
            )
        await msg.edit(
            content=f"Tournament ended! The winner is {remain[0].mention}.\nMoney was given!"
        )


def setup(bot):
    bot.add_cog(Tournament(bot))
