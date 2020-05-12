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
# This is an implementation of Werewolf: The Pact
# The Pact includes the extensions:
# - New Moon
# - The Community
# - Characters
# I have left out the raven and the pyro from "The Community"
# the house part is not my favourite
# The "New Moon" cards are also not included, hence
# the shake and the gypsy are not here
# "Werewolf" is a game by Philippe des Pallières and Hervé Marly
# Thank you for making such an awesome game!
from __future__ import annotations

import asyncio
import random

from enum import Enum
from typing import List, Optional

import discord

from async_timeout import timeout
from discord.ext import commands

from classes.context import Context


class Role(Enum):
    WEREWOLF = 1
    BIG_BAD_WOLF = 2

    VILLAGER = 3
    PURE_SOUL = 4
    SEER = 5
    AMOR = 6
    WITCH = 7
    HUNTER = 8
    HEALER = 9
    THE_OLD = 10
    SISTER = 11
    BROTHER = 12
    FOX = 13
    JUDGE = 14
    KNIGHT = 15

    WHITE_WOLF = 16
    THIEF = 17
    MAID = 18
    WILD_CHILD = 19
    WOLFHOUND = 20

    FLUTIST = 21


class Side(Enum):
    VILLAGERS = 1
    WOLVES = 2
    WHITE_WOLF = 3
    FLUTIST = 4


DESCRIPTIONS = {
    Role.WEREWOLF: (
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill - choose carefully!"
    ),
    Role.BIG_BAD_WOLF: (
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill together with them."
        " After that, you will wake up once more to kill an additional villager."
    ),
    Role.VILLAGER: (
        "You are an innocent soul. Your goal is to eradicate all Werewolves that are"
        " haunting the town at nights and survive yourself. At the daily elections,"
        " your voice makes the difference."
    ),
    Role.PURE_SOUL: (
        "Everyone knows you are not a Werewolf. Your goal is to keep the town safe from"
        " Wolves and kill them all - at the daily elections, many will hear your voice,"
        " they know you will be honest."
    ),
    Role.SEER: (
        "You are a villager with the special ability to view someone's identity every"
        " night - but don't tell the villagers too fast, else you will be targeted"
        " yourself."
    ),
    Role.AMOR: (
        "You are the personification of the Greek god and get to choose two lovers at"
        " the beginning of the game - they will love each other so much that they will"
        " die once their beloved one bites the dust."
    ),
    Role.WITCH: (
        "You are a powerful villager with two special brews: One will kill, one will"
        " heal. Use them wisely to influence the game in your favor."
    ),
    Role.HUNTER: (
        "You are the Hunter. Do your best to protect the Community and your precise"
        " shot will trigger when you die, killing a target of your choice."
    ),
    Role.HEALER: (
        "You are the Healer. Every night, you can protect one Villager from death to"
        " the Werewolves, but not the same person twice. Make sure the Villagers stay"
        " alive..."
    ),
    Role.THE_OLD: (
        "You are the oldest member of the community and the Werewolves have been"
        " hurting you for a long time. All the years have granted you a lot of"
        " resistance - you can survive one attack."
    ),
    Role.SISTER: (
        "The two sisters know each other very well - together, you might be able to"
        " help the community find the Werewolves and eliminate them."
    ),
    Role.BROTHER: (
        "The three brothers know each other very well - together, you might be able to"
        " help the community find the Werewolves and eliminate them."
    ),
    Role.FOX: (
        "You are a clever little guy who can sense the presence of Werewolves. Every"
        " night, you get to choose 3 players and will be told if at least one of them"
        " is a Werewolf. If not, you lose your ability."
    ),
    Role.JUDGE: (
        "You are the Judge. You love the law and can arrange a second daily vote after"
        " the first one by mentioning the secret sign we will agree on later during the"
        " vote. Use it wisely..."
    ),
    Role.KNIGHT: (
        "You are the Knight. You will do your best to protect the Villagers from the"
        " Werewolves. When you die, a Werewolf will die with you."
    ),
    Role.WHITE_WOLF: (
        "You are the White Wolf. Your objective is to kill everyone else. Additionally"
        " to the nightly killing spree with the Werewolves, you may kill one of them"
        " later on in the night."
    ),
    Role.THIEF: "You are the thief and can choose your identity soon.",
    Role.WILD_CHILD: (
        "You are the wild child and will choose an idol. Once it dies, you turn into a"
        " Werewolf, but until then, you are a normal Villager..."
    ),
    Role.WOLFHOUND: (
        "You are something between a Werewolf and a Villager. Choose your side"
        " wisely..."
    ),
    Role.MAID: (
        "You are the maid who raised the children. It would hurt you to see any of them"
        " die - after the daily election, you may take their identity role once."
    ),
    Role.FLUTIST: (
        "You are the flutist. Your goal is to enchant the players with your music to"
        " take revenge for being expelled many years ago. Every night, you get to"
        " enchant two of them. Gotta catch them all..."
    ),
}


class Game:
    def __init__(self, ctx: Context, players: List[discord.Member]) -> None:
        self.ctx = ctx
        self.available_roles = get_roles(len(players))
        self.available_roles, self.extra_roles = (
            self.available_roles[:-2],
            self.available_roles[-2:],
        )
        self.players: List[Player] = [
            Player(role, user, self)
            for role, user in zip(self.available_roles, players)
        ]
        random.choice(self.players).is_sheriff = True
        self.judge_spoken = False
        self.judge_symbol = None

    @property
    def sheriff(self) -> Player:
        return discord.utils.get(self.players, is_sheriff=True)

    @property
    def alive_players(self) -> List[Player]:
        return [player for player in self.players if not player.dead]

    def get_players_with_role(self, role: Role) -> List[Player]:
        return [player for player in self.alive_players if player.role == role]

    def get_player_with_role(self, role: Role) -> Optional[Player]:
        return discord.utils.get(self.alive_players, role=role)

    def winner(self) -> Optional[Player]:
        objective_reached = discord.utils.get(self.alive_players, has_won=True)
        if objective_reached:
            return objective_reached
        if len(self.alive_players) < 2:
            try:
                return self.alive_players[0]
            except IndexError:
                return "No one"

    @property
    def lovers(self) -> List[Player]:
        return [player for player in self.alive_players if player.in_love]

    @property
    def new_afk_players(self) -> List[Player]:
        return [player for player in self.alive_players if player.to_check_afk]

    async def wolves(self) -> Optional[Player]:
        healer = self.get_player_with_role(Role.HEALER)
        if healer:
            await self.ctx.send("**The healer awakes...**")
            protected = await healer.get_healer_target()
        else:
            protected = None
        wolves = [
            p
            for p in self.alive_players
            if p.side == Side.WOLVES or p.side == Side.WHITE_WOLF
        ]
        if len(wolves) == 0:
            return
        wolves_users = [str(p.user.id) for p in wolves]
        await self.ctx.send("**The werewolves awake...**")
        # Get target of wolves
        possible_targets = {
            idx: p for idx, p in enumerate(self.alive_players, 1) if p not in wolves
        }
        fmt = commands.Paginator(prefix="", suffix="")
        fmt.add_line("**It is time to choose a victim**")
        fmt.add_line("All possible users are:")
        for idx, p in possible_targets.items():
            fmt.add_line(f"{idx}. {p.user}")
        fmt.add_line("")
        fmt.add_line(
            "**I will relay all messages you send to the other Werewolves. Send a"
            " number to nominate them for killing (you can nominate up to 10 users),"
            " voting starts in 2 minutes**"
        )
        fmt.add_line(
            "**Please do not spam and talk slowly! Relaying can take a while if there"
            " are many Werewolves!**"
        )
        for user in wolves:
            for page in fmt.pages:
                await user.send(page)
        nominated = []
        try:
            async with timeout(120):
                while len(nominated) < 10:
                    msg = await self.ctx.bot.wait_for_dms(
                        "message", check={"author": {"id": wolves_users}}
                    )
                    if msg.content.isdigit() and int(msg.content) in possible_targets:
                        nominated.append(possible_targets[int(msg.content)])
                        text = f"**{msg.author}** nominated **{nominated[-1].user}**"
                    else:
                        text = f"**{msg.author}**: {msg.content}"
                    for user in wolves:
                        await user.send(text)
        except asyncio.TimeoutError:
            pass
        if not nominated:
            return None
        nominated = {u: 0 for u in nominated}
        nominated_users = [str(u.user) for u in nominated]
        if len(nominated) > 1:
            for user in wolves:
                await user.send("The voting is starting, please wait for your turn...")
            for user in wolves:
                try:
                    target = await self.ctx.bot.paginator.Choose(
                        entries=nominated_users,
                        return_index=True,
                        title="Vote for a target",
                    ).paginate(self.ctx, location=user.user)
                except self.ctx.bot.paginator.NoChoice:
                    continue
                nominated[list(nominated.keys())[target]] += 1
            targets = sorted(list(nominated.keys()), key=lambda x: -nominated[x])
            if nominated[targets[0]] > nominated[targets[1]]:
                target = targets[0]
            else:
                target = None
        else:
            target = list(nominated.keys())[0]
        if target == protected:
            return None
        else:
            return target

    async def initial_preparation(self) -> List[Player]:
        await self.ctx.send("**Sending game roles...**")
        for player in self.players:
            await player.send_information()
        thief = self.get_player_with_role(Role.THIEF)
        if thief:
            await self.ctx.send("**The thief awakes...**")
            await thief.choose_role_from(self.extra_roles)
        wolfhound = self.get_player_with_role(Role.WOLFHOUND)
        if wolfhound:
            await self.ctx.send("**The Wolfhound awakes...**")
            await wolfhound.choose_role_from([Role.VILLAGER, Role.WEREWOLF])
        amor = self.get_player_with_role(Role.AMOR)
        if amor:
            await self.ctx.send("**Amor awakes and shoots his arrows...**")
            await amor.choose_lovers()
        pure_soul = self.get_player_with_role(Role.PURE_SOUL)
        if pure_soul:
            await self.ctx.send(
                f"{pure_soul.user.mention} is a pure soul and an innocent villager."
            )
        seer = self.get_player_with_role(Role.SEER)
        if seer:
            await self.ctx.send("**The seer awakes...**")
            await seer.check_player_card()
        fox = self.get_player_with_role(Role.FOX)
        if fox:
            await self.ctx.send("**The fox awakes...**")
            await fox.check_3_werewolves()
        if amor:
            lover1 = self.lovers[0]
            lover2 = self.lovers[1]
            await lover1.send_love_msg(lover2)
            await lover2.send_love_msg(lover1)
        judge = self.get_player_with_role(Role.JUDGE)
        if judge:
            await self.ctx.send("**The judge awakes...**")
            self.judge_symbol = await judge.get_judge_symbol()
        sisters = self.get_players_with_role(Role.SISTER)
        if sisters:
            await self.ctx.send("**The sisters awake...**")
            for player in sisters:
                await player.send_family_msg("sister", sisters)
        brothers = self.get_players_with_role(Role.BROTHER)
        if brothers:
            await self.ctx.send("**The brothers awake...**")
            for player in brothers:
                await player.send_family_msg("brother", brothers)
        wild_child = self.get_player_with_role(Role.WILD_CHILD)
        if wild_child:
            await self.ctx.send("**The wild child awakes and chooses its idol...**")
            await wild_child.choose_idol()
        target = await self.wolves()
        targets = [target] if target is not None else []
        if (
            sum(
                1
                for player in self.players
                if player.dead and player.role == Role.WEREWOLF
            )
            == 0
        ):
            big_bad_wolf = self.get_player_with_role(Role.BIG_BAD_WOLF)
            if big_bad_wolf:
                await self.ctx.send("**The big, bad wolf awakes...**")
                targets.append(await big_bad_wolf.choose_villager_to_kill())
        witch = self.get_player_with_role(Role.WITCH)
        if witch:
            await self.ctx.send("**The witch awakes...**")
            targets = await witch.witch_actions(targets)
        flutist = self.get_player_with_role(Role.FLUTIST)
        if flutist:
            await self.ctx.send("**The flutist awakes...**")
            possible_targets = [
                p for p in self.alive_players if not p.enchanted and p != flutist
            ]
            await flutist.enchant(possible_targets)
        final_targets = targets[:]
        for target in targets:
            if target.in_love:
                final_targets.append([p for p in self.lovers if p != target][0])
        return final_targets

    async def night(self, white_wolf_ability: bool) -> List[Player]:
        seer = self.get_player_with_role(Role.SEER)
        if seer:
            await self.ctx.send("**The seer awakes...**")
            await seer.check_player_card()
        fox = self.get_player_with_role(Role.FOX)
        if fox:
            await self.ctx.send("**The fox awakes...**")
            await fox.check_3_werewolves()
        target = await self.wolves()
        targets = [target] if target is not None else []
        if white_wolf_ability:
            white_wolf = self.get_player_with_role(Role.WHITE_WOLF)
            if white_wolf:
                await self.ctx.send("**The white wolf awakes...**")
                target = await white_wolf.choose_werewolf()
                if target:
                    targets.append(target)
        if (
            sum(
                1
                for player in self.players
                if player.dead and player.role == Role.WEREWOLF
            )
            == 0
        ):
            big_bad_wolf = self.get_player_with_role(Role.BIG_BAD_WOLF)
            if big_bad_wolf:
                await self.ctx.send("**The big, bad wolf awakes...**")
                targets.append(await big_bad_wolf.choose_villager_to_kill())
        witch = self.get_player_with_role(Role.WITCH)
        if witch:
            await self.ctx.send("**The witch awakes...**")
            targets = await witch.witch_actions(targets)
        flutist = self.get_player_with_role(Role.FLUTIST)
        if flutist:
            possible_targets = [
                p for p in self.alive_players if not p.enchanted and p != flutist[0]
            ]
            await self.ctx.send("**The flutist awakes...**")
            await flutist.enchant(possible_targets)
        return targets

    async def election(self) -> Optional[discord.Member]:
        text = " ".join([u.user.mention for u in self.alive_players])
        await self.ctx.send(
            f"{text}\nYou may now submit someone (up to 10 total) for the election who"
            " to kill by mentioning their name below. You have 3 minutes of discussion"
            " during this time."
        )
        nominated = []
        second_election = False
        eligible_players = [player.user for player in self.alive_players]
        try:
            async with timeout(180):
                while len(nominated) < 10:
                    msg = await self.ctx.bot.wait_for(
                        "message",
                        check=lambda x: x.author in eligible_players
                        and x.channel.id == self.ctx.channel.id
                        and (
                            len(x.mentions) > 0
                            or (
                                x.content == self.judge_symbol and not self.judge_spoken
                            )
                        ),
                    )
                    if msg.content == self.judge_symbol:
                        second_election = True
                        self.judge_spoken = True
                    for user in msg.mentions:
                        if (
                            user in eligible_players
                            and user not in nominated
                            and len(nominated) < 10
                        ):
                            nominated.append(user)
                            await self.ctx.send(f"{msg.author} nominated someone.")
        except asyncio.TimeoutError:
            pass
        if not nominated:
            return None, second_election
        if len(nominated) == 1:
            return nominated[0], second_election
        emojis = ([f"{index+1}\u20e3" for index in range(9)] + ["\U0001f51f"])[
            : len(nominated)
        ]
        texts = "\n".join(
            [f"{emoji} - {user.mention}" for emoji, user in zip(emojis, nominated)]
        )
        msg = await self.ctx.send(
            f"**React to vote for killing someone. You have 60 seconds.**\n{texts}"
        )
        for emoji in emojis:
            await msg.add_reaction(emoji)
        await asyncio.sleep(60)
        msg = await self.ctx.channel.fetch_message(msg.id)
        nominated = {u: 0 for u in nominated}
        mapping = {emoji: user for emoji, user in zip(emojis, nominated)}
        voters = []
        for reaction in msg.reactions:
            if str(reaction.emoji) in emojis:
                nominated[mapping[str(reaction.emoji)]] = sum(
                    [1 async for user in reaction.users() if user in eligible_players]
                )
                voters += [
                    user
                    async for user in reaction.users()
                    if user in eligible_players and user not in voters
                ]
        failed_voters = [
            failed_voter
            for failed_voter in eligible_players
            if failed_voter not in voters
        ]
        for player in self.alive_players:
            if player.user in failed_voters:
                player.to_check_afk = True
        new_mapping = sorted(list(mapping.values()), key=lambda x: -nominated[x])
        return (
            (
                new_mapping[0]
                if len(new_mapping) == 1
                or nominated[new_mapping[0]] > nominated[new_mapping[1]]
                else None
            ),
            second_election,
        )

    async def handle_afk(self) -> None:
        if len(self.new_afk_players) < 1:
            return
        for player in self.new_afk_players:
            player.to_check_afk = False
            if await player.is_afk():
                player.afk_strikes += 1
                if player.afk_strikes >= 3:
                    if not player.dead:
                        await player.send(
                            "Strike 3! You have been killed by the game after"
                            " having 3 strikes of being AFK."
                        )
                        await self.ctx.send(
                            f"**{player.user.mention}** has been killed by"
                            " the game due to having 3 strikes of AFK."
                        )
                        await player.kill()
                else:
                    await player.send(
                        f"**Strike {player.afk_strikes}!** You have been marked"
                        " as AFK. You'll be killed after 3 strikes."
                    )
            else:
                await player.send("You're not AFK.")

    async def day(self, deaths: List[Player]) -> None:
        for death in deaths:
            await death.kill()
        if len(self.alive_players) < 2:
            return
        if self.winner() is not None:
            return
        to_kill, second_election = await self.election()
        if to_kill is not None:
            await self.ctx.send(f"The community has decided to kill {to_kill.mention}.")
            to_kill = discord.utils.get(self.alive_players, user=to_kill)
            await to_kill.kill()
            if to_kill.dead:
                maid = self.get_player_with_role(Role.MAID)
                if maid:
                    await maid.handle_maid(to_kill)
        else:
            await self.ctx.send("Indecisively, the community has killed noone.")
        await self.handle_afk()
        if second_election:
            to_kill, second_election = await self.election()
            if to_kill is not None:
                await self.ctx.send(
                    f"The community has decided to kill {to_kill.mention}."
                )
                to_kill = discord.utils.get(self.alive_players, user=to_kill)
                await to_kill.kill()
                if to_kill.dead:
                    maid = self.get_player_with_role(Role.MAID)
                    if maid:
                        await maid.handle_maid(to_kill)
            else:
                await self.ctx.send(
                    "Indecisively, the community has not lynched anyone."
                )
            await self.handle_afk()

    async def run(self):
        # Handle thief etc and first night
        deaths = await self.initial_preparation()
        round_no = 1
        night_no = 1
        while self.winner() is None:
            if round_no % 2 == 1:
                await self.day(deaths)
            else:
                night_no += 1
                deaths = await self.night(white_wolf_ability=night_no % 2 == 0)
            round_no += 1

        winner = self.winner()
        if isinstance(winner, Player):
            await self.ctx.send(
                f"{winner.user.mention} won! They were a"
                f" **{winner.role.name.lower().replace('_', ' ')}**!"
            )
            if len(self.alive_players) > 1:
                players_to_reveal = [
                    "{player_name} were a **{role_name}**!{initial_role_info}".format(
                        player_name=player.user.mention,
                        role_name=player.role.name.lower().replace("_", " "),
                        initial_role_info=(
                            f" A **{player.initial_role.name.lower().replace('_', ' ')}**"
                            " initially."
                        )
                        if player.role != player.initial_role
                        else "",
                    )
                    for player in self.alive_players
                    if player != winner
                ]
                text_reveal = "\n ".join(players_to_reveal)
                await self.ctx.send(
                    "The game has ended. I will now reveal the other living"
                    f" players' roles:\n{text_reveal}"
                )
        else:
            await self.ctx.send(f"{winner} won!")


class Player:
    def __init__(self, role: Role, user: discord.Member, game: Game) -> None:
        self.role = role
        self.initial_role = role
        self.user = user
        self.game = game
        self.is_sheriff = False
        self.enchanted = False
        self.in_love = False
        self.idol = None

        # Witch
        self.can_heal = True
        self.can_kill = True

        # Healer
        self.last_target = None

        if role == Role.THE_OLD:
            self.lives = 2
        else:
            self.lives = 1

        # AFK check
        self.afk_strikes = 0
        self.to_check_afk = False

    def __repr__(self):
        return (
            f"<Player role={self.role} initial_role={self.initial_role}"
            f" is_sheriff={self.is_sheriff} lives={self.lives} side={self.side}"
            f" dead={self.dead} won={self.has_won}>"
        )

    async def send(self, *args, **kwargs) -> Optional[discord.Message]:
        try:
            return await self.user.send(*args, **kwargs)
        except discord.Forbidden:
            pass

    async def choose_users(
        self, title: str, list_of_users: List[Player], amount: int
    ) -> List[Player]:
        fmt = [f"{idx}. {p.user}" for idx, p in enumerate(list_of_users, 1)]
        paginator = commands.Paginator(prefix="", suffix="")
        paginator.add_line(f"**{title}**")
        for i in fmt:
            paginator.add_line(i)
        for page in paginator.pages:
            await self.send(page)
        mymsg = await self.send(
            "**Type the number of the user to choose for this action. You need to"
            f" choose {amount} more.**"
        )
        chosen = []
        while len(chosen) < amount:
            msg = await self.game.ctx.bot.wait_for_dms(
                "message",
                check={
                    "author": {"id": str(self.user.id)},
                    "content": [str(i) for i in range(1, len(list_of_users) + 1)],
                },
            )
            player = list_of_users[int(msg.content) - 1]
            chosen.append(player)
            await mymsg.edit(
                content=(
                    "**Type the number of the user to choose for this action. You need"
                    f" to choose {amount - len(chosen)} more.**"
                )
            )
        return chosen

    async def send_information(self) -> None:
        await self.send(
            "You are a"
            f" **{self.role.name.lower().replace('_', ' ')}**\n\n{DESCRIPTIONS[self.role]}"
        )

    async def send_love_msg(self, lover: Player) -> None:
        await self.send(
            f"You are in love with {lover.user}! Amor really knew you had an eye on"
            " them..."
        )

    async def choose_idol(self) -> None:
        possible_idols = [p for p in self.game.players if p != self]
        try:
            idol = await self.choose_users(
                "Choose your Idol. You will turn into a Werewolf if they die.",
                list_of_users=possible_idols,
                amount=1,
            )
        except asyncio.TimeoutError:
            idol = [random.choice(possible_idols)]
            await self.send(
                "You didn't choose anything. A random player will be chosen for you."
            )
        if idol:
            self.idol = idol[0]
        await self.send(f"{self.idol.user} became your Idol.")

    async def get_judge_symbol(self) -> str:
        await self.send(
            "Please enter a phrase that will trigger a second election. It is case"
            " sensitive."
        )
        try:
            msg = await self.game.ctx.bot.wait_for_dms(
                "message", check={"author": {"id": str(self.user.id)}}
            )
            symbol = msg.content
        except asyncio.TimeoutError:
            symbol = "hahayes"
        await self.user.send(
            f"The phrase is **{symbol}**. Enter it right within 10 seconds after an"
            " election to trigger another one."
        )
        return symbol

    async def handle_maid(self, death: Player) -> None:
        if self.in_love:
            return
        try:
            action = await self.game.ctx.bot.paginator.Choose(
                entries=["Yes", "No"],
                return_index=True,
                title=f"Would you like to swap cards with {death.user}?",
            ).paginate(self.game.ctx, location=self.user)
        except self.game.ctx.bot.paginator.NoChoice:
            return
        if action == 0:
            self.enchanted = False
            if self.is_sheriff:
                self.is_sheriff = False
                random.choice(self.game.alive_players).is_sheriff = True
            self.role = death.role

    async def get_healer_target(self) -> Player:
        available = [
            player for player in self.game.alive_players if player != self.last_target
        ]
        try:
            target = await self.choose_users(
                "Choose a user to protect from Werewolves.",
                list_of_users=available,
                amount=1,
            )
        except asyncio.TimeoutError:
            target = [random.choice(available)]
        self.last_target = target[0]

        return target[0]

    async def choose_werewolf(self) -> Optional[Player]:
        possible_targets = [p for p in self.game.alive_players if p.side == Side.WOLVES]
        try:
            target = await self.choose_users(
                "Choose a Werewolf to kill.", list_of_users=possible_targets, amount=1
            )
        except asyncio.TimeoutError:
            return None
        return target[0]

    async def choose_villager_to_kill(self) -> Player:
        possible_targets = [
            p
            for p in self.game.alive_players
            if p.side not in (Side.WOLVES, Side.WHITE_WOLF)
        ]
        try:
            target = await self.choose_users(
                "Choose a Villager to kill.", list_of_users=possible_targets, amount=1
            )
        except asyncio.TimeoutError:
            return None
        return target[0]

    async def witch_actions(self, targets: List[Player]) -> Player:
        if any(targets) and self.can_heal:
            try:
                to_heal = await self.choose_users(
                    "Choose someone to heal.", list_of_users=targets, amount=1
                )
                if to_heal:
                    targets.remove(to_heal[0])
                    self.can_heal = False
            except asyncio.TimeoutError:
                pass
        if self.can_kill:
            possible_targets = [
                p for p in self.game.alive_players if p != self and p not in targets
            ]
            try:
                to_kill = await self.choose_users(
                    "Choose someone to poison.",
                    list_of_users=possible_targets,
                    amount=1,
                )
                if to_kill:
                    targets.append(to_kill[0])
                    self.can_kill = False
            except asyncio.TimeoutError:
                pass
        return targets

    async def enchant(self, possible_targets: List[Player]) -> None:
        if len(possible_targets) > 2:
            try:
                to_enchant = await self.choose_users(
                    "Choose 2 people to enchant.",
                    list_of_users=possible_targets,
                    amount=2,
                )
            except asyncio.TimeoutError:
                to_enchant = []
        else:
            to_enchant = possible_targets
        for p in to_enchant:
            p.enchanted = True

    async def send_family_msg(self, relationship: str, family: List[Player]) -> None:
        await self.send(
            f"Your {relationship}(s) are/is:"
            f" {'and'.join([str(u.user) for u in family])}"
        )

    async def check_player_card(self) -> None:
        try:
            to_inspect = (
                await self.choose_users(
                    "Choose someone whose identity you would like to see.",
                    list_of_users=[u for u in self.game.alive_players if u != self],
                    amount=1,
                )
            )[0]
        except asyncio.TimeoutError:
            return
        await self.send(
            f"{to_inspect.user} is a"
            f" **{to_inspect.role.name.lower().replace('_', ' ')}**"
        )

    async def choose_role_from(self, roles: List[Role]) -> None:
        entries = [role.name.title().replace("_", " ") for role in roles]
        await self.send(
            "You will be asked to choose a new role from these:\n**{choices}**".format(
                choices=", ".join(entries)
            )
        )
        try:
            can_dm = True
            role = await self.game.ctx.bot.paginator.Choose(
                entries=entries, return_index=True, title="Choose a new role",
            ).paginate(self.game.ctx, location=self.user)
            role = roles[role]
        except self.game.ctx.bot.paginator.NoChoice:
            role = random.choice(roles)
            await self.send(
                "You didn't choose anything. A random role was chosen for you."
            )
        except discord.Forbidden:
            can_dm = False
            role = random.choice(roles)
            await self.game.ctx.send(
                "I couldn't send a DM. A random role was chosen for them."
            )
        self.role = role
        if can_dm:
            await self.send(
                f"Your new role is now **{self.role.name.title().replace('_', ' ')}**."
            )

    async def check_3_werewolves(self):
        try:
            targets = await self.choose_users(
                "Choose 3 people who you want to see if any if a werewolf.",
                list_of_users=[u for u in self.game.alive_players if u != self],
                amount=3,
            )
        except asyncio.TimeoutError:
            return
        if not any(
            [target.side in (Side.WOLVES, Side.WHITE_WOLF) for target in targets]
        ):
            self.role = Role.VILLAGER
            await self.send("You found no Werewolf and are now a villager.")
        else:
            await self.send("One of them is a Werewolf.")

    async def choose_lovers(self) -> None:
        try:
            lovers = await self.choose_users(
                "Choose 2 lovers", list_of_users=self.game.players, amount=2
            )
        except asyncio.TimeoutError:
            lovers = random.sample(self.game.players, 2)
            await self.send("Timed out. Lovers will be chosen randomly.")
        for lover in lovers:
            lover.in_love = True
        await self.send(
            f"You've made **{lovers[0].user}** and **{lovers[1].user}** lovers."
        )

    @property
    def dead(self) -> bool:
        return self.lives < 1

    async def kill(self) -> None:
        self.lives -= 1
        if self.dead:
            await self.game.ctx.send(
                f"{self.user.mention} has died. They were a"
                f" **{self.role.name.lower().replace('_', ' ')}**!"
            )
            wild_child = discord.utils.find(
                lambda x: x.idol is not None, self.game.alive_players
            )
            if wild_child and wild_child.idol == self:
                wild_child.role = Role.WEREWOLF
                await wild_child.send(
                    f"Your idol {self.user} died, you turned into a **Werewolf**."
                )
            lovers = self.game.lovers
            if self.in_love and len(lovers) == 1:
                other = lovers[0]
                await self.game.ctx.send(
                    f"{self.user.mention}'s lover {other.user.mention} will die as"
                    " well."
                )
                await other.kill()
            if self.role == Role.HUNTER:
                try:
                    target = await self.choose_users(
                        "Choose someone who shall die together with you.",
                        list_of_users=self.game.alive_players,
                        amount=1,
                    )
                except asyncio.TimeoutError:
                    return
                await self.game.ctx.send("The hunter is firing.")
                await target[0].kill()
            elif self.role == Role.KNIGHT:
                target = random.choice(
                    [
                        p
                        for p in self.game.alive_players
                        if p.side in (Side.WOLVES, Side.WHITE_WOLF)
                    ]
                )
                await self.game.ctx.send(
                    "The Knight is striking a final time with his sword."
                )
                await target.kill()

    @property
    def side(self) -> Side:
        if 1 <= self.role.value <= 2:
            return Side.WOLVES
        if 3 <= self.role.value <= 15:
            return Side.VILLAGERS
        else:
            return getattr(Side, self.role.name, "NAN")

    @property
    def has_won(self) -> bool:
        # Returns whether the player has reached their goal or not
        if self.side == Side.VILLAGERS:
            return not any(
                [
                    player.side == Side.WOLVES or player.side == Side.WHITE_WOLF
                    for player in self.game.alive_players
                ]
            )
        elif self.side == Side.WOLVES:
            return all(
                [
                    player.side == Side.WOLVES or player.side == Side.WHITE_WOLF
                    for player in self.game.alive_players
                ]
            )
        elif self.side == Side.WHITE_WOLF:
            return len(self.game.players) == 1 and not self.dead
        elif self.side == Side.FLUTIST:
            return all(
                [
                    player.enchanted or player == self
                    for player in self.game.alive_players
                ]
            )

    async def is_afk(self) -> bool:
        await self.send("You failed to vote. This is just an AFK check:")

        async def for_reaction():
            try:
                answer = await self.game.ctx.bot.paginator.Choose(
                    entries=[
                        "Yes",
                        "I'm still in the game",
                        "Of course I am",
                        "Please don't kill me!",
                    ],
                    return_index=True,
                    title="Are you still in the game? You have 30 seconds to answer.",
                ).paginate(self.game.ctx, location=self.user)
            except (
                self.game.ctx.bot.paginator.NoChoice,
                discord.errors.Forbidden,
                asyncio.TimeoutError,
            ):
                answer = None
            return answer

        async def for_dms():
            try:
                msg = await self.game.ctx.bot.wait_for(
                    "message",
                    check=lambda x: x.author.id == self.user.id
                    and (
                        x.channel.id == self.game.ctx.channel.id
                        or x.channel.id == self.user.dm_channel.id
                    ),
                )
                answer = msg.content
            except (
                discord.errors.Forbidden,
                asyncio.TimeoutError,
            ):
                answer = None
            return answer

        done, pending = await asyncio.wait(
            [for_reaction(), for_dms(),], return_when=asyncio.FIRST_COMPLETED
        )
        try:
            answer = done.pop().result()
        except asyncio.TimeoutError:
            answer = None
        return answer is None


# A list of roles to give depending on the number of total players
# Rule of thumb is to have 50+% of villagers, whereas thief etc count
# as wolves as there is a good chance they might become some
# This is the main subject to change for game balance
ROLES_FOR_PLAYERS: List[Role] = [
    Role.VILLAGER,
    Role.VILLAGER,
    Role.WEREWOLF,
    Role.SEER,
    Role.WITCH,
    Role.HUNTER,
    Role.THIEF,
    Role.WEREWOLF,
    Role.WILD_CHILD,
    Role.PURE_SOUL,
    Role.MAID,
    Role.VILLAGER,
    Role.WHITE_WOLF,
    Role.HEALER,
    Role.AMOR,
    Role.KNIGHT,
    Role.SISTER,
    Role.SISTER,
    Role.BIG_BAD_WOLF,
    Role.THE_OLD,
    Role.WEREWOLF,
    Role.WOLFHOUND,
    Role.WEREWOLF,
    Role.FOX,
    Role.BROTHER,
    Role.BROTHER,
    Role.BROTHER,
    Role.JUDGE,
    Role.FLUTIST,
    Role.WEREWOLF,
    Role.VILLAGER,
]


def get_roles(number_of_players: int) -> List[Role]:
    number_of_players += 2  # Thief is in play
    if number_of_players > len(ROLES_FOR_PLAYERS):
        roles = ROLES_FOR_PLAYERS
        # Fill up with villagers and wolves as all special roles are taken
        for i in range(number_of_players - len(roles)):
            if i % 2 == 0:
                roles.append(Role.WEREWOLF)
            else:
                roles.append(Role.VILLAGER)
    else:
        roles = ROLES_FOR_PLAYERS[:number_of_players]
    if sum(1 for role in roles if role == Role.SISTER) == 1:
        for idx, role in enumerate(roles):
            if role == Role.SISTER:
                roles[idx] = Role.VILLAGER
    if sum(1 for role in roles if role == Role.BROTHER) < 3:
        for idx, role in enumerate(roles):
            if role == Role.BROTHER:
                roles[idx] = Role.VILLAGER
    random.shuffle(roles)
    return roles


if __name__ == "__main__":
    game = Game(50)
    game.run()
