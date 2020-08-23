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
import asyncio
import datetime
import math

from collections import deque
from decimal import Decimal

import discord

from discord.ext import commands

from classes.converters import IntFromTo
from cogs.help import chunks
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import random
from utils.checks import has_char, user_has_char
from utils.i18n import _, locale_doc


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(1800)
    @commands.command(brief=_("Start a new tournament"))
    @locale_doc
    async def tournament(self, ctx, prize: IntFromTo(0, 100_000_000) = 0):
        _(
            """`[prize]` - The amount of money the winner will get

            Start a new tournament. Players have 30 seconds to join via the reaction.
            Tournament entries are free, only the tournament host has to pay the price.

            Only an exponent of 2 (2^n) users can join. If there are more than the nearest exponent, the last joined players will be disregarded.

            The match-ups will be decided at random, the battles themselves will be decided like regular battles (see `{prefix}help battle` for details).

            The winner of a match moves onto the next round, the losers get eliminated, until there is only one player left.
            Tournaments in IdleRPG follow the single-elimination principle.

            (This command has a cooldown of 30 minutes.)"""
        )
        if ctx.character_data["money"] < prize:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You are too poor."))

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            prize,
            ctx.author.id,
        )
        await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-prize)

        if ctx.channel.id == self.bot.config.official_tournament_channel_id:
            id_ = await self.bot.start_joins()
            await ctx.send(
                "A mass-tournament has been started. Please join at"
                f" https://join.idlerpg.xyz/{id_} during the next 10 minutes! The"
                f" prize is **${prize}**!"
            )
            await asyncio.sleep(60 * 10)
            a_participants = await self.bot.get_joins(id_)
            participants = []
            async with self.bot.pool.acquire() as conn:
                for u in a_participants:
                    if await self.bot.cache.get_profile(u.id, conn=conn):
                        participants.append(u)

        else:
            msg = await ctx.send(
                _(
                    "{author} started a tournament! Free entries, prize is"
                    " **${prize}**! React with ⚔ to join!"
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
                        await self.bot.reset_cooldown(ctx)
                        await self.bot.pool.execute(
                            'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                            prize,
                            ctx.author.id,
                        )
                        await self.bot.cache.update_profile_cols_rel(
                            ctx.author.id, money=prize
                        )
                        return await ctx.send(
                            _("Noone joined your tournament {author}.").format(
                                author=ctx.author.mention
                            )
                        )
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
                    "There are **{num}** entries, due to the fact we need a playable"
                    " tournament, the last **{removed}** have been removed."
                ).format(num=len(participants), removed=len(participants) - toremove)
            )
            participants = participants[: -(len(participants) - toremove)]
        else:
            await ctx.send(
                _("Tournament started with **{num}** entries.").format(num=toremove)
            )
        text = _("vs")
        while len(participants) > 1:
            participants = random.shuffle(participants)
            matches = list(chunks(participants, 2))

            for match in matches:
                await ctx.send(f"{match[0].mention} {text} {match[1].mention}")
                await asyncio.sleep(2)
                async with self.bot.pool.acquire() as conn:
                    val1 = sum(
                        await self.bot.get_damage_armor_for(match[0], conn=conn)
                    ) + random.randint(1, 7)
                    val2 = sum(
                        await self.bot.get_damage_armor_for(match[1], conn=conn)
                    ) + random.randint(1, 7)
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

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                prize,
                participants[0].id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=participants[0].id,
                subject="money",
                data={"Amount": prize},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(participants[0].id, money=prize)
        await msg.edit(
            content=_(
                "Tournament ended! The winner is {winner}.\nMoney was given!"
            ).format(winner=participants[0].mention)
        )

    @has_char()
    @user_cooldown(1800)
    @commands.command()
    @locale_doc
    async def raidtournament(self, ctx, prize: IntFromTo(0, 100_000_000) = 0):
        _(
            """`[prize]` - The amount of money the winner will get

            Start a new raid tournament. Players have 30 seconds to join via the reaction.
            Tournament entries are free, only the tournament host has to pay the price.

            Only an exponent of 2 (2^n) users can join. If there are more than the nearest exponent, the last joined players will be disregarded.

            The match-ups will be decided at random, the battles themselves will be decided like raid battles (see `{prefix}help raidbattle` for details).

            The winner of a match moves onto the next round, the losers get eliminated, until there is only one player left.
            Tournaments in IdleRPG follow the single-elimination principle.

            (This command has a cooldown of 30 minutes.)"""
        )
        if ctx.character_data["money"] < prize:
            await self.bot.reset_cooldown(ctx)
            return await ctx.send(_("You are too poor."))

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            prize,
            ctx.author.id,
        )
        await self.bot.cache.update_profile_cols_rel(ctx.author.id, money=-prize)

        if ctx.channel.id == self.bot.config.official_tournament_channel_id:
            id_ = await self.bot.start_joins()
            await ctx.send(
                "A mass-raidtournament has been started. Please join at"
                f" https://join.idlerpg.xyz/{id_} during the next 10 minutes! The"
                f" prize is **${prize}**!"
            )
            await asyncio.sleep(60 * 10)
            a_participants = await self.bot.get_joins(id_)
            participants = []
            async with self.bot.pool.acquire() as conn:
                for u in a_participants:
                    if await self.bot.cache.get_profile(u.id, conn=conn):
                        participants.append(u)

        else:
            msg = await ctx.send(
                _(
                    "{author} started a raid tournament! Free entries, prize is"
                    " **${prize}**! React with ⚔ to join!"
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
                        await self.bot.reset_cooldown(ctx)
                        await self.bot.pool.execute(
                            'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                            prize,
                            ctx.author.id,
                        )
                        await self.bot.cache.update_profile_cols_rel(
                            ctx.author.id, money=prize
                        )
                        return await ctx.send(
                            _("Noone joined your raid tournament {author}.").format(
                                author=ctx.author.mention
                            )
                        )
                    break
                if await user_has_char(self.bot, u.id):
                    if u in participants:
                        continue
                    participants.append(u)
                    await ctx.send(
                        _("{user} joined the raidtournament.").format(user=u.mention)
                    )
                else:
                    await ctx.send(
                        _("You don't have a character, {user}.").format(user=u.mention)
                    )
        toremove = 2 ** math.floor(math.log2(len(participants)))
        if toremove != len(participants):
            await ctx.send(
                _(
                    "There are **{num}** entries, due to the fact we need a playable"
                    " raid tournament, the last **{removed}** have been removed."
                ).format(num=len(participants), removed=len(participants) - toremove)
            )
            participants = participants[: -(len(participants) - toremove)]
        else:
            await ctx.send(
                _("Tournament started with **{num}** entries.").format(num=toremove)
            )
        text = _("vs")
        while len(participants) > 1:
            participants = random.shuffle(participants)
            matches = list(chunks(participants, 2))

            for match in matches:
                await ctx.send(f"{match[0].mention} {text} {match[1].mention}")

                players = []

                async with self.bot.pool.acquire() as conn:
                    for player in match:
                        dmg, deff = await self.bot.get_raidstats(player, conn=conn)
                        u = {
                            "user": player,
                            "hp": 250,
                            "armor": deff,
                            "damage": dmg,
                        }
                        players.append(u)

                battle_log = deque(
                    [
                        (
                            0,
                            _("Raidbattle {p1} vs. {p2} started!").format(
                                p1=players[0]["user"], p2=players[1]["user"]
                            ),
                        )
                    ],
                    maxlen=3,
                )

                embed = discord.Embed(
                    description=battle_log[0][1], color=self.bot.config.primary_colour,
                )

                log_message = await ctx.send(embed=embed)
                await asyncio.sleep(4)

                start = datetime.datetime.utcnow()
                attacker, defender = random.shuffle(players)
                while (
                    attacker["hp"] > 0
                    and defender["hp"] > 0
                    and datetime.datetime.utcnow()
                    < start + datetime.timedelta(minutes=5)
                ):
                    # this is where the fun begins
                    dmg = (
                        attacker["damage"]
                        + Decimal(random.randint(0, 100))
                        - defender["armor"]
                    )
                    dmg = 1 if dmg <= 0 else dmg  # make sure no negative damage happens
                    defender["hp"] -= dmg
                    if defender["hp"] < 0:
                        defender["hp"] = 0
                    battle_log.append(
                        (
                            battle_log[-1][0] + 1,
                            _(
                                "{attacker} attacks! {defender} takes **{dmg}HP**"
                                " damage."
                            ).format(
                                attacker=attacker["user"].mention,
                                defender=defender["user"].mention,
                                dmg=dmg,
                            ),
                        )
                    )

                    embed = discord.Embed(
                        description=_(
                            "{p1} - {hp1} HP left\n{p2} - {hp2} HP left"
                        ).format(
                            p1=players[0]["user"],
                            hp1=players[0]["hp"],
                            p2=players[1]["user"],
                            hp2=players[1]["hp"],
                        ),
                        color=self.bot.config.primary_colour,
                    )

                    for line in battle_log:
                        embed.add_field(
                            name=_("Action #{number}").format(number=line[0]),
                            value=line[1],
                        )

                    await log_message.edit(embed=embed)
                    await asyncio.sleep(4)
                    attacker, defender = defender, attacker  # switch places
                if players[0]["hp"] == 0:
                    winner = match[1]
                    looser = match[0]
                else:
                    winner = match[0]
                    looser = match[1]
                participants.remove(looser)
                await ctx.send(
                    _("Winner of this match is {winner}!").format(winner=winner.mention)
                )
                await asyncio.sleep(2)

        await ctx.send(_("Round Done!"))

        msg = await ctx.send(
            _("Raid Tournament ended! The winner is {winner}.").format(
                winner=participants[0].mention
            )
        )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                prize,
                participants[0].id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=participants[0].id,
                subject="money",
                data={"Amount": prize},
                conn=conn,
            )
        await self.bot.cache.update_profile_cols_rel(participants[0].id, money=prize)
        await msg.edit(
            content=_(
                "Raid Tournament ended! The winner is {winner}.\nMoney was given!"
            ).format(winner=participants[0].mention)
        )


def setup(bot):
    bot.add_cog(Tournament(bot))
