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
import asyncio
import datetime

from collections import deque
from decimal import Decimal

import discord

from discord.enums import ButtonStyle
from discord.ext import commands
from discord.ui.button import Button

from classes.classes import Ranger
from classes.classes import from_string as class_from_string
from classes.converters import IntGreaterThan
from cogs.shard_communication import user_on_cooldown as user_cooldown
from utils import random
from utils.checks import has_char, has_money
from utils.i18n import _, locale_doc
from utils.joins import SingleJoinView


class Battles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @has_char()
    @user_cooldown(90)
    @commands.command(brief=_("Battle against another player"))
    @locale_doc
    async def battle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _(
            """`[money]` - A whole number that can be 0 or greater; defaults to 0
            `[enemy]` - A user who has a profile; defaults to anyone

            Fight against another player while betting money.
            To decide the fight, the players' items, race and class bonuses and an additional number from 1 to 7 are evaluated, this serves as a way to give players with lower stats a chance at winning.

            The money is removed from both players at the start of the battle. Once a winner has been decided, they will receive their money, plus the enemy's money.
            The battle lasts 30 seconds, after which the winner and loser will be mentioned.

            If both players' stats + random number are the same, the winner is decided at random.
            The battle's winner will receive a PvP win, which shows on their profile.
            (This command has a cooldown of 90 seconds.)"""
        )
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            money,
            ctx.author.id,
        )

        if not enemy:
            text = _("{author} seeks a battle! The price is **${money}**.").format(
                author=ctx.author.mention, money=money
            )
        else:
            _(
                "{author} seeks a battle with {enemy}! The price is **${money}**."
            ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)

        async def check(user: discord.User) -> bool:
            return await has_money(self.bot, user.id, money)

        future = asyncio.Future()
        view = SingleJoinView(
            future,
            Button(
                style=ButtonStyle.primary,
                label=_("Join the battle!"),
                emoji="\U00002694",
            ),
            allowed=enemy,
            prohibited=ctx.author,
            timeout=60,
            check=check,
            check_fail_message=_("You don't have enough money to join the battle."),
        )

        await ctx.send(text, view=view)

        try:
            enemy_ = await future
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            return await ctx.send(
                _("Noone wanted to join your battle, {author}!").format(
                    author=ctx.author.mention
                )
            )

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;', money, enemy_.id
        )

        await ctx.send(
            _(
                "Battle **{author}** vs **{enemy}** started! 30 seconds of fighting"
                " will now start!"
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

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "pvpwins"="pvpwins"+1, "money"="money"+$1 WHERE'
                ' "user"=$2;',
                money * 2,
                winner.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=looser.id,
                to=winner.id,
                subject="money",
                data={"Amount": money},
                conn=conn,
            )
        await ctx.send(
            _("{winner} won the battle vs {looser}! Congratulations!").format(
                winner=winner.mention, looser=looser.mention
            )
        )

    @has_char()
    @user_cooldown(300)
    @commands.command(brief=_("Battle against a player (inclusdes raidstats)"))
    @locale_doc
    async def raidbattle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _(
            """`[money]` - A whole number that can be 0 or greater; defaults to 0
            `[enemy]` - A user who has a profile; defaults to anyone

            Fight against another player while betting money.
            To decide the players' stats, their items, race and class bonuses and raidstats are evaluated.

            The money is removed from both players at the start of the battle. Once a winner has been decided, they will receive their money, plus the enemy's money.
            The battle is divided into rounds, in which a player attacks. The first round's attacker is chosen randomly, all other rounds the attacker is the last round's defender.

            The battle ends if one player's HP drops to 0 (winner decided), or if 5 minutes after the battle started pass (tie).
            In case of a tie, both players will get their money back.

            The battle's winner will receive a PvP win, which shows on their profile.
            (This command has a cooldown of 5 minutes)"""
        )
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            money,
            ctx.author.id,
        )

        if not enemy:
            text = _("{author} seeks a raidbattle! The price is **${money}**.").format(
                author=ctx.author.mention, money=money
            )
        else:
            _(
                "{author} seeks a raidbattle with {enemy}! The price is **${money}**."
            ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)

        async def check(user: discord.User) -> bool:
            return await has_money(self.bot, user.id, money)

        future = asyncio.Future()
        view = SingleJoinView(
            future,
            Button(
                style=ButtonStyle.primary,
                label=_("Join the raidbattle!"),
                emoji="\U00002694",
            ),
            allowed=enemy,
            prohibited=ctx.author,
            timeout=60,
            check=check,
            check_fail_message=_("You don't have enough money to join the raidbattle."),
        )

        await ctx.send(text, view=view)

        try:
            enemy_ = await future
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            return await ctx.send(
                _("Noone wanted to join your raidbattle, {author}!").format(
                    author=ctx.author.mention
                )
            )

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;', money, enemy_.id
        )

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
            description=battle_log[0][1], color=self.bot.config.game.primary_colour
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
                color=self.bot.config.game.primary_colour,
            )

            for line in battle_log:
                embed.add_field(
                    name=_("Action #{number}").format(number=line[0]), value=line[1]
                )

            await log_message.edit(embed=embed)
            await asyncio.sleep(4)
            attacker, defender = defender, attacker  # switch places

        players = sorted(players, key=lambda x: x["hp"])
        winner = players[1]["user"]
        looser = players[0]["user"]

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"+$1, "pvpwins"="pvpwins"+1 WHERE'
                ' "user"=$2;',
                money * 2,
                winner.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=looser.id,
                to=winner.id,
                subject="money",
                data={"Amount": money},
                conn=conn,
            )
        await ctx.send(
            _("{p1} won the raidbattle vs {p2}! Congratulations!").format(
                p1=winner.mention, p2=looser.mention
            )
        )

    @has_char()
    @user_cooldown(600)
    @commands.command(brief=_("Battle against a player (active)"))
    @locale_doc
    async def activebattle(
        self, ctx, money: IntGreaterThan(-1) = 0, enemy: discord.Member = None
    ):
        _(
            """`[money]` - A whole number that can be 0 or greater; defaults to 0
            `[enemy]` - A user who has a profile; defaults to anyone

            Fight against another player while betting money.
            To decide players' stats, their items, race and class bonuses are evaluated.

            The money is removed from both players at the start of the battle. Once a winner has been decided, they will receive their money, plus the enemy's money.
            The battle takes place in rounds. Each round, both players have to choose their move using the reactions.
            Players can attack (⚔️), defend (🛡️) or recover HP (❤️).

            The battle ends if one player's HP drops to 0 (winner decided), or a player does not move (forfeit).
            In case of a forfeit, neither of the players will get their money back.

            The battle's winner will receive a PvP win, which shows on their profile.
            (This command has a cooldown of 10 minutes.)"""
        )
        if enemy == ctx.author:
            return await ctx.send(_("You can't battle yourself."))
        if ctx.character_data["money"] < money:
            return await ctx.send(_("You are too poor."))

        await self.bot.pool.execute(
            'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
            money,
            ctx.author.id,
        )

        if not enemy:
            text = _(
                "{author} seeks an active battle! The price is **${money}**."
            ).format(author=ctx.author.mention, money=money)
        else:
            text = _(
                "{author} seeks an active battle with {enemy}! The price is **${money}**."
            ).format(author=ctx.author.mention, enemy=enemy.mention, money=money)

        async def check(user: discord.User) -> bool:
            return await has_money(self.bot, user.id, money)

        future = asyncio.Future()
        view = SingleJoinView(
            future,
            Button(
                style=ButtonStyle.primary,
                label=_("Join the activebattle!"),
                emoji="\U00002694",
            ),
            allowed=enemy,
            prohibited=ctx.author,
            timeout=60,
            check=check,
            check_fail_message=_(
                "You don't have enough money to join the activebattle."
            ),
        )

        await ctx.send(text, view=view)

        try:
            enemy_ = await future
        except asyncio.TimeoutError:
            await self.bot.reset_cooldown(ctx)
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                money,
                ctx.author.id,
            )
            return await ctx.send(
                _("Noone wanted to join your activebattle, {author}!").format(
                    author=ctx.author.mention
                )
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

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "money"="money"-$1 WHERE "user"=$2;',
                money,
                enemy_.id,
            )

            for p in players:
                classes = [
                    class_from_string(i)
                    for i in await conn.fetchval(
                        'SELECT class FROM profile WHERE "user"=$1;', p.id
                    )
                ]
                if any(c.in_class_line(Ranger) for c in classes if c):
                    players[p]["hp"] = 120
                else:
                    players[p]["hp"] = 100

                attack, defense = await self.bot.get_damage_armor_for(p, conn=conn)
                players[p]["damage"] = int(attack)
                players[p]["defense"] = int(defense)

        moves = {
            "\U00002694": "attack",
            "\U0001f6e1": "defend",
            "\U00002764": "recover",
        }

        msg = await ctx.send(
            _("Battle {p1} vs {p2}").format(p1=ctx.author.mention, p2=enemy_.mention),
            embed=discord.Embed(
                title=_("Let the battle begin!"),
                color=self.bot.config.game.primary_colour,
            ),
        )

        def is_valid_move(r, u):
            return str(r.emoji) in moves and u in players and r.message.id == msg.id

        for emoji in moves:
            await msg.add_reaction(emoji)

        while players[ctx.author]["hp"] > 0 and players[enemy_]["hp"] > 0:
            await msg.edit(
                embed=discord.Embed(
                    description=_(
                        "{prevaction}\n{player1}: **{hp1}** HP\n{player2}: **{hp2}**"
                        " HP\nReact to play."
                    ).format(
                        prevaction="\n".join([i["lastmove"] for i in players.values()]),
                        player1=ctx.author.mention,
                        player2=enemy_.mention,
                        hp1=players[ctx.author]["hp"],
                        hp2=players[enemy_]["hp"],
                    )
                )
            )
            players[ctx.author]["action"], players[enemy_]["action"] = None, None
            players[ctx.author]["lastmove"], players[enemy_]["lastmove"] = (
                _("{user} does nothing...").format(user=ctx.author.mention),
                _("{user} does nothing...").format(user=enemy_.mention),
            )

            while (not players[ctx.author]["action"]) or (
                not players[enemy_]["action"]
            ):
                try:
                    r, u = await self.bot.wait_for(
                        "reaction_add", timeout=30, check=is_valid_move
                    )
                    try:
                        await msg.remove_reaction(r.emoji, u)
                    except discord.Forbidden:
                        pass
                except asyncio.TimeoutError:
                    await self.bot.reset_cooldown(ctx)
                    await self.bot.pool.execute(
                        'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2 or "user"=$3;',
                        money,
                        ctx.author.id,
                        enemy_.id,
                    )
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
            await self.bot.pool.execute(
                'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2 or "user"=$3;',
                money,
                ctx.author.id,
                enemy_.id,
            )
            return await ctx.send(_("You both died!"))
        if players[ctx.author]["hp"] > players[enemy_]["hp"]:
            winner, looser = ctx.author, enemy_
        else:
            looser, winner = ctx.author, enemy_
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                'UPDATE profile SET "pvpwins"="pvpwins"+1, "money"="money"+$1 WHERE'
                ' "user"=$2;',
                money * 2,
                winner.id,
            )
            await self.bot.log_transaction(
                ctx,
                from_=looser.id,
                to=winner.id,
                subject="money",
                data={"Amount": money},
                conn=conn,
            )
        await msg.edit(
            embed=discord.Embed(
                description=_(
                    "{prevaction}\n{player1}: **{hp1}** HP\n{player2}: **{hp2}**"
                    " HP\nReact to play."
                ).format(
                    prevaction="\n".join([i["lastmove"] for i in players.values()]),
                    player1=ctx.author.mention,
                    player2=enemy_.mention,
                    hp1=players[ctx.author]["hp"],
                    hp2=players[enemy_]["hp"],
                )
            )
        )
        await ctx.send(
            _("{winner} won the active battle vs {looser}! Congratulations!").format(
                winner=winner.mention,
                looser=looser.mention,
            )
        )


def setup(bot):
    bot.add_cog(Battles(bot))
