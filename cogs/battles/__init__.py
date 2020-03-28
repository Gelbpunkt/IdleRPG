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
import random

from collections import deque
from decimal import Decimal

import discord

from discord.ext import commands

from classes.converters import IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils.checks import has_char, has_money


class Battles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(90)
    @commands.command()
    @locale_doc
    async def battle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _("""Battle against another player.""")
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        if not enemy:
            msg = await ctx.send(
                _(
                    "{author} seeks a battle! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, money=money)
            )
        else:
            msg = await ctx.send(
                _(
                    "{author} seeks a battle with {enemy}! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)
            )

        def check(r, u):
            if enemy:
                if u != enemy:
                    return False
            return (
                str(r.emoji) == "\U00002694"
                and r.message.id == msg.id
                and u != ctx.author
                and not u.bot
            )

        await msg.add_reaction("\U00002694")
        seeking = True

        while seeking:
            try:
                reaction, enemy_ = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )
            except asyncio.TimeoutError:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("Noone wanted to join your battle, {author}!").format(
                        author=ctx.author.mention
                    )
                )
            if await has_money(self.bot, enemy_.id, money):
                seeking = False
            else:
                enemy_ = None
                await ctx.send(_("You don't have enough money to join the battle."))

        await ctx.send(
            _(
                "Battle **{author}** vs **{enemy}** started! 30 seconds of fighting will now start!"
            ).format(author=ctx.disp, enemy=enemy_.display_name)
        )
        stats = [
            sum(await self.bot.get_damage_armor_for(ctx.author)) + random.randint(1, 7),
            sum(await self.bot.get_damage_armor_for(enemy_)) + random.randint(1, 7),
        ]
        players = [ctx.author, enemy_]
        if stats[0] == stats[1]:
            winner = random.choice(players)
        else:
            winner = players[stats.index(max(stats))]
        looser = players[players.index(winner) - 1]

        await asyncio.sleep(30)

        if not await has_money(self.bot, winner.id, money) or not await has_money(
            self.bot, looser.id, money
        ):
            return await ctx.send(
                _(
                    "One of you can't pay the price for the battle because he spent money in the time of fighting."
                )
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
        await self.bot.log_transaction(
            ctx, from_=looser.id, to=winner.id, subject="money", data={"Amount": money}
        )
        await ctx.send(
            _("{winner} won the battle vs {looser}! Congratulations!").format(
                winner=winner.mention, looser=looser.mention
            )
        )

    @has_char()
    @user_cooldown(300)
    @commands.command()
    @locale_doc
    async def raidbattle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _("""Battle system based on raids.""")
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        if not enemy:
            msg = await ctx.send(
                _(
                    "{author} seeks a raidbattle! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, money=money)
            )
        else:
            msg = await ctx.send(
                _(
                    "{author} seeks a raidbattle with {enemy}! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)
            )

        def check(r, u):
            if enemy:
                if u != enemy:
                    return False
            return (
                str(r.emoji) == "\U00002694"
                and r.message.id == msg.id
                and u != ctx.author
                and not u.bot
            )

        await msg.add_reaction("\U00002694")
        seeking = True

        while seeking:
            try:
                reaction, enemy_ = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )
            except asyncio.TimeoutError:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("Noone wanted to join your raidbattle, {author}!").format(
                        author=ctx.author.mention
                    )
                )
            if await has_money(self.bot, enemy_.id, money):
                seeking = False
            else:
                enemy_ = None
                await ctx.send(_("You don't have enough money to join the raidbattle."))

        players = []

        async with self.bot.pool.acquire() as conn:
            for player in (ctx.author, enemy_):
                dmg, deff = await self.bot.get_raidstats(player, conn=conn)
                u = {"user": player, "hp": 250, "armor": deff, "damage": dmg}
                players.append(u)

        # players[0] is the author, players[1] is the enemy

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
            description=battle_log[0][1], color=self.bot.config.primary_colour
        )

        log_message = await ctx.send(
            embed=embed
        )  # we'll edit this message later to avoid spam
        await asyncio.sleep(4)

        start = datetime.datetime.utcnow()
        attacker, defender = random.sample(
            players, k=2
        )  # decide a random attacker and defender for the first iteration

        while (
            players[0]["hp"] > 0
            and players[1]["hp"] > 0
            and datetime.datetime.utcnow() < start + datetime.timedelta(minutes=5)
        ):
            # this is where the fun begins
            dmg = (
                attacker["damage"] + Decimal(random.randint(0, 100)) - defender["armor"]
            )
            dmg = 1 if dmg <= 0 else dmg  # make sure no negative damage happens
            defender["hp"] -= dmg
            if defender["hp"] < 0:
                defender["hp"] = 0
            battle_log.append(
                (
                    battle_log[-1][0] + 1,
                    _(
                        "{attacker} attacks! {defender} takes **{dmg}HP** damage."
                    ).format(
                        attacker=attacker["user"].mention,
                        defender=defender["user"].mention,
                        dmg=dmg,
                    ),
                )
            )

            embed = discord.Embed(
                description=_("{p1} - {hp1} HP left\n{p2} - {hp2} HP left").format(
                    p1=players[0]["user"],
                    hp1=players[0]["hp"],
                    p2=players[1]["user"],
                    hp2=players[1]["hp"],
                ),
                color=self.bot.config.primary_colour,
            )

            for line in battle_log:
                embed.add_field(
                    name=_("Action #{number}").format(number=line[0]), value=line[1]
                )

            await log_message.edit(embed=embed)
            await asyncio.sleep(4)
            attacker, defender = defender, attacker  # switch places

        if players[1]["hp"] == 0:  # command author wins
            if not await has_money(
                self.bot, ctx.author.id, money
            ) or not await has_money(self.bot, enemy_.id, money):
                return await ctx.send(
                    _(
                        "One of you both can't pay the price for the raidbattle because he spent money in the time of fighting."
                    )
                )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    money,
                    enemy_.id,
                )
                await conn.execute(
                    'UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=$1;',
                    ctx.author.id,
                )
            await self.bot.log_transaction(
                ctx,
                from_=enemy_.id,
                to=ctx.author.id,
                subject="money",
                data={"Amount": money},
            )
            await ctx.send(
                _("{p1} won the raidbattle vs {p2}! Congratulations!").format(
                    p1=ctx.author.mention, p2=enemy_.mention
                )
            )
        elif players[0]["hp"] == 0:  # enemy wins
            if not await has_money(
                self.bot, ctx.author.id, money
            ) or not await has_money(self.bot, enemy_.id, money):
                return await ctx.send(
                    _(
                        "One of you both can't pay the price for the raidbattle because he spent money in the time of fighting."
                    )
                )
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE profile SET money=money+$1 WHERE "user"=$2;',
                    money,
                    enemy_.id,
                )
                await conn.execute(
                    'UPDATE profile SET money=money-$1 WHERE "user"=$2;',
                    money,
                    ctx.author.id,
                )
                await conn.execute(
                    'UPDATE profile SET pvpwins=pvpwins+1 WHERE "user"=$1;', enemy_.id
                )
            await self.bot.log_transaction(
                ctx,
                from_=ctx.author.id,
                to=enemy_.id,
                subject="money",
                data={"Amount": money},
            )
            await ctx.send(
                _("{p1} won the raidbattle vs {p2}! Congratulations!").format(
                    p1=enemy_.mention, p2=ctx.author.mention
                )
            )

        else:  # timeout after 5 min
            await ctx.send(_("Raidbattle took too long, aborting."))

    @has_char()
    @user_cooldown(600)
    @commands.command()
    @locale_doc
    async def activebattle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _("""Reaction-based battle system.""")
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        if not enemy:
            msg = await ctx.send(
                _(
                    "{author} seeks an active battle! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, money=money)
            )
        else:
            msg = await ctx.send(
                _(
                    "{author} seeks an active battle with {enemy}! React with ⚔ now to duel them! The price is **${money}**."
                ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)
            )

        def check(r, u):
            if enemy:
                if u != enemy:
                    return False
            return (
                str(r.emoji) == "\U00002694"
                and r.message.id == msg.id
                and u != ctx.author
                and not u.bot
            )

        await msg.add_reaction("\U00002694")
        seeking = True

        while seeking:
            try:
                reaction, enemy_ = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check
                )
            except asyncio.TimeoutError:
                await self.bot.reset_cooldown(ctx)
                return await ctx.send(
                    _("Noone wanted to join your activebattle, {author}!").format(
                        author=ctx.author.mention
                    )
                )
            if await has_money(self.bot, enemy_.id, money):
                seeking = False
            else:
                enemy_ = None
                await ctx.send(
                    _("You don't have enough money to join the activebattle.")
                )

        players = {
            ctx.author: {
                "hp": 0,
                "damage": 0,
                "defense": 0,
                "lastmove": "",
                "action": None,
            },
            enemy_: {
                "hp": 0,
                "damage": 0,
                "defense": 0,
                "lastmove": "",
                "action": None,
            },
        }

        for p in players:
            c = await self.bot.pool.fetchval(
                'SELECT class FROM profile WHERE "user"=$1;', p.id
            )
            if self.bot.in_class_line(c, "Ranger"):
                players[p]["hp"] = 120
            else:
                players[p]["hp"] = 100

            d, a = await self.bot.get_damage_armor_for(p)
            players[p]["damage"] = int(d)
            players[p]["defense"] = int(a)

        moves = {
            "\U00002694": "attack",
            "\U0001f6e1": "defend",
            "\U00002764": "recover",
        }

        last = None

        def is_valid_move(r, u):
            return str(r.emoji) in moves and u in players and r.message.id == last.id

        while players[ctx.author]["hp"] > 0 and players[enemy_]["hp"] > 0:
            last = await ctx.send(
                _(
                    "{prevaction}\n{player1}: **{hp1}** HP\n{player2}: **{hp2}** HP\nReact to play."
                ).format(
                    prevaction="\n".join([i["lastmove"] for i in players.values()]),
                    player1=ctx.author.mention,
                    player2=enemy_.mention,
                    hp1=players[ctx.author]["hp"],
                    hp2=players[enemy_]["hp"],
                )
            )
            players[ctx.author]["action"], players[enemy_]["action"] = None, None
            players[ctx.author]["lastmove"], players[enemy_]["lastmove"] = (
                _("{user} does nothing...").format(user=ctx.author.mention),
                _("{user} does nothing...").format(user=enemy_.mention),
            )
            for emoji in moves:
                await last.add_reaction(emoji)

            while (not players[ctx.author]["action"]) or (
                not players[enemy_]["action"]
            ):
                try:
                    r, u = await self.bot.wait_for(
                        "reaction_add", timeout=30, check=is_valid_move
                    )
                except asyncio.TimeoutError:
                    await self.bot.reset_cooldown(ctx)
                    return await ctx.send(
                        _("Someone refused to move. Activebattle stopped.")
                    )
                if not players[u]["action"]:
                    players[u]["action"] = moves[str(r.emoji)]
                else:
                    playerlist = list(players.keys())
                    await ctx.send(
                        _(
                            "{user}, you already moved! Waiting for {other}'s move..."
                        ).format(
                            user=u.mention,
                            other=playerlist[1 - playerlist.index(u)].mention,
                        )
                    )
            plz = list(players.keys())
            for idx, user in enumerate(plz):
                other = plz[1 - idx]
                if players[user]["action"] == "recover":
                    heal_hp = round(players[user]["damage"] * 0.25) or 1
                    players[user]["hp"] += heal_hp
                    players[user]["lastmove"] = _(
                        "{user} healed themselves for **{hp} HP**."
                    ).format(user=user.mention, hp=heal_hp)
                elif (
                    players[user]["action"] == "attack"
                    and players[other]["action"] != "defend"
                ):
                    eff = random.choice(
                        [
                            players[user]["damage"],
                            int(players[user]["damage"] * 0.5),
                            int(players[user]["damage"] * 0.2),
                            int(players[user]["damage"] * 0.8),
                        ]
                    )
                    players[other]["hp"] -= eff
                    players[user]["lastmove"] = _(
                        "{user} hit {enemy} for **{eff}** damage."
                    ).format(user=user.mention, enemy=other.mention, eff=eff)
                elif (
                    players[user]["action"] == "attack"
                    and players[other]["action"] == "defend"
                ):
                    eff = random.choice(
                        [
                            int(players[user]["damage"]),
                            int(players[user]["damage"] * 0.5),
                            int(players[user]["damage"] * 0.2),
                            int(players[user]["damage"] * 0.8),
                        ]
                    )
                    eff2 = random.choice(
                        [
                            int(players[other]["defense"]),
                            int(players[other]["defense"] * 0.5),
                            int(players[other]["defense"] * 0.2),
                            int(players[other]["defense"] * 0.8),
                        ]
                    )
                    if eff - eff2 > 0:
                        players[other]["hp"] -= eff - eff2
                        players[user]["lastmove"] = _(
                            "{user} hit {enemy} for **{eff}** damage."
                        ).format(user=user.mention, enemy=other.mention, eff=eff - eff2)
                        players[other]["lastmove"] = _(
                            "{enemy} tried to defend, but failed.".format(
                                enemy=other.mention
                            )
                        )

                    else:
                        players[user]["lastmove"] = _(
                            "{user}'s attack on {enemy} failed!"
                        ).format(user=user.mention, enemy=other.mention)
                        players[other]["lastmove"] = _(
                            "{enemy} blocked {user}'s attack.".format(
                                enemy=other.mention, user=user.mention
                            )
                        )
                elif players[user]["action"] == players[other]["action"] == "defend":
                    players[ctx.author]["lastmove"] = _("You both tried to defend.")
                    players[enemy_]["lastmove"] = _("It was not very effective...")

        if players[ctx.author]["hp"] <= 0 and players[enemy_]["hp"] <= 0:
            return await ctx.send(_("You both died!"))
        if players[ctx.author]["hp"] > players[enemy_]["hp"]:
            winner, looser = ctx.author, enemy_
        else:
            looser, winner = ctx.author, enemy_
        if not await has_money(self.bot, winner.id, money) or not await has_money(
            self.bot, looser.id, money
        ):
            return await ctx.send(
                _(
                    "One of you both can't pay the price for the activebattle because he spent money in the time of fighting."
                )
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
        await self.bot.log_transaction(
            ctx, from_=looser.id, to=winner.id, subject="money", data={"Amount": money}
        )
        await ctx.send(
            _(
                "{prevaction}\n{winner} won the active battle vs {looser}! Congratulations!"
            ).format(
                prevaction="\n".join([players[p]["lastmove"] for p in players]),
                winner=winner.mention,
                looser=looser.mention,
            )
        )


def setup(bot):
    bot.add_cog(Battles(bot))
