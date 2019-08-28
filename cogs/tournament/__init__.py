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
import asyncio
import math
import random

from discord.ext import commands

from classes.converters import IntFromTo
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_money, user_has_char


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(1800)
    @commands.command()
    @locale_doc
    async def tournament(self, ctx, prize: IntFromTo(0, 100_000_000)):
        _("""Starts a new tournament.""")
        if ctx.character_data["money"] < prize:
            return await ctx.send(_("You are too poor."))
        msg = await ctx.send(
            _(
                "{author} started a tournament! Free entries, prize is **${prize}**! React with ⚔ to join!"
            ).format(author=ctx.author.mention, prize=prize)
        )
        participants = [ctx.author]

        await msg.add_reaction("\U00002694")

        def simplecheck(r, u):
            return (
                r.message.id == msg.id
                and u not in participants
                and str(r.emoji) == "\U00002694"
                and not u.bot
            )

        while True:
            try:
                r, u = await self.bot.wait_for(
                    "reaction_add", timeout=30, check=simplecheck
                )
            except asyncio.TimeoutError:
                if len(participants) < 2:
                    return await ctx.send(_("Noone joined your tournament."))
                break
            if await user_has_char(self.bot, u.id):
                if u in participants:
                    # May be that we're too slow and user reacting too fast
                    continue
                participants.append(u)
                await ctx.send(
                    _("{user} joined the tournament.").format(user=u.mention)
                )
            else:
                await ctx.send(
                    _("You don't have a character, {user}.").format(user=u.mention)
                )
        toremove = 2 ** math.floor(math.log2(len(participants)))
        if toremove != len(participants):
            await ctx.send(
                _(
                    "There are **{num}** entries, due to the fact we need a playable tournament, the last **{removed}** have been removed."
                ).format(num=len(participants), removed=len(participants) - toremove)
            )
            participants = participants[: -(len(participants) - toremove)]
        else:
            await ctx.send(
                _("Tournament started with **{num}** entries.").format(num=toremove)
            )
        text = _("vs")
        while len(participants) > 1:
            random.shuffle(participants)
            matches = list(chunks(participants, 2))

            for match in matches:
                await ctx.send(f"{match[0].mention} {text} {match[1].mention}")
                await asyncio.sleep(2)
                sw1, sh1 = await self.bot.get_equipped_items_for(match[0])
                sw2, sh2 = await self.bot.get_equipped_items_for(match[1])
                val1 = (
                    (sw1["damage"] if sw1 else 0)
                    + (sh1["armor"] if sh1 else 0)
                    + random.randint(1, 7)
                )
                val2 = (
                    (sw2["damage"] if sw2 else 0)
                    + (sh2["armor"] if sh2 else 0)
                    + random.randint(1, 7)
                )
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
                await ctx.send(
                    _("Winner of this match is {winner}!").format(winner=winner.mention)
                )
                await asyncio.sleep(2)

            await ctx.send(_("Round Done!"))

        msg = await ctx.send(
            _("Tournament ended! The winner is {winner}.").format(
                winner=participants[0].mention
            )
        )
        if not await has_money(self.bot, ctx.author.id, prize):
            return await ctx.send(_("The creator spent money, prize can't be given!"))
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
            content=_(
                "Tournament ended! The winner is {winner}.\nMoney was given!"
            ).format(winner=participants[0].mention)
        )


def setup(bot):
    bot.add_cog(Tournament(bot))
