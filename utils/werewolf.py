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
import datetime

from enum import Enum
from typing import List, Optional, Union

import discord

from async_timeout import timeout
from discord.ext import commands

from classes.context import Context
from cogs.help import chunks
from utils import random
from utils.i18n import _


class Role(Enum):
    WEREWOLF = 1
    BIG_BAD_WOLF = 2
    CURSED_WOLF_FATHER = 3
    WOLF_SHAMAN = 4
    WOLF_NECROMANCER = 5

    VILLAGER = 6
    PURE_SOUL = 7
    SEER = 8
    AMOR = 9
    WITCH = 10
    HUNTER = 11
    HEALER = 12
    THE_OLD = 13
    SISTER = 14
    BROTHER = 15
    FOX = 16
    JUDGE = 17
    KNIGHT = 18
    MAID = 19
    WILD_CHILD = 20
    THIEF = 21
    PARAGON = 22
    RITUALIST = 23
    TROUBLEMAKER = 24
    LAWYER = 25
    WAR_VETERAN = 26

    WHITE_WOLF = 27
    WOLFHOUND = 28
    RAIDER = 29

    FLUTIST = 30


class Side(Enum):
    VILLAGERS = 1
    WOLVES = 2
    WHITE_WOLF = 3
    FLUTIST = 4


DESCRIPTIONS = {
    Role.WEREWOLF: _(
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill - choose carefully!"
    ),
    Role.BIG_BAD_WOLF: _(
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill together with them."
        " After that, you will wake up once more to kill an additional villager, but as"
        " long as no Werewolf or Wild Child has been killed."
    ),
    Role.VILLAGER: _(
        "You are an innocent soul. Your goal is to eradicate all Werewolves that are"
        " haunting the town at nights and survive yourself. At the daily elections,"
        " your voice makes the difference."
    ),
    Role.PURE_SOUL: _(
        "Everyone knows you are not a Werewolf. Your goal is to keep the town safe from"
        " Wolves and kill them all - at the daily elections, many will hear your voice,"
        " they know you will be honest."
    ),
    Role.SEER: _(
        "You are a villager with the special ability to view someone's identity every"
        " night - but don't tell the villagers too fast, else you will be targeted"
        " yourself."
    ),
    Role.AMOR: _(
        "You are the personification of the Greek god and get to choose two lovers at"
        " the beginning of the game - they will love each other so much that they will"
        " die once their beloved one bites the dust."
    ),
    Role.WITCH: _(
        "You are a powerful villager with two special brews: One will kill, one will"
        " heal. Use them wisely to influence the game in your favor."
    ),
    Role.HUNTER: _(
        "You are the Hunter. Do your best to protect the Community and your precise"
        " shot will trigger when you die, killing a target of your choice."
    ),
    Role.HEALER: _(
        "You are the Healer. Every night, you can protect one Villager from death to"
        " the Werewolves, but not the same person twice in a row. Make sure the"
        " Villagers stay alive..."
    ),
    Role.THE_OLD: _(
        "You are the oldest member of the community and the Werewolves have been"
        " hurting you for a long time. All the years have granted you a lot of"
        " resistance - you can survive one attack from the Werewolves. The Village's"
        " Vote, Witch, and Hunter will kill you on the first time, and upon dying, all"
        " the other Villagers will lose their special powers and become normal"
        " villagers."
    ),
    Role.SISTER: _(
        "The two sisters know each other very well - together, you might be able to"
        " help the community find the Werewolves and eliminate them."
    ),
    Role.BROTHER: _(
        "The three brothers know each other very well - together, you might be able to"
        " help the community find the Werewolves and eliminate them."
    ),
    Role.FOX: _(
        "You are a clever little guy who can sense the presence of Werewolves. Every"
        " night, you get to choose a group of 3 neighboring players of which you point"
        " the center player and will be told if at least one of them is a Werewolf. If"
        " you do not find a Werewolf, you lose your ability for good."
    ),
    Role.JUDGE: _(
        "You are the Judge. You love the law and can arrange a second daily vote after"
        " the first one by mentioning the secret sign we will agree on later during the"
        " vote. Use it wisely..."
    ),
    Role.KNIGHT: _(
        "You are the Rusty Sword Knight. You will do your best to protect the"
        " Villagers. If you died from the Werewolves, a random Werewolf who caused your"
        " death becomes diseased from your rusty sword and will die the following"
        " night."
    ),
    Role.WHITE_WOLF: _(
        "You are the White Wolf. Your objective is to kill everyone else. Additionally"
        " to the nightly killing spree with the Werewolves, you may kill one of them"
        " later on in the night."
    ),
    Role.THIEF: _("You are the Thief and can choose your identity soon."),
    Role.WILD_CHILD: _(
        "You are the Wild Child and will choose an idol. Once it dies, you turn into a"
        " Werewolf, but until then, you are a normal Villager..."
    ),
    Role.WOLFHOUND: _(
        "You are something between a Werewolf and a Villager. Choose your side"
        " wisely..."
    ),
    Role.MAID: _(
        "You are the Maid who raised the children. It would hurt you to see any of them"
        " die - after the daily election, you may take their identity role once."
    ),
    Role.FLUTIST: _(
        "You are the Flutist. Your goal is to enchant the players with your music to"
        " take revenge for being expelled many years ago. Every night, you get to"
        " enchant two of them. Gotta catch them all..."
    ),
    Role.CURSED_WOLF_FATHER: _(
        "You are the Cursed Wolf Father that has the ability to spread your curse. Your"
        " objective is to kill all villagers together with the other Werewolves. Every"
        " night, you will get to choose one villager to kill together with them. You"
        " may, once, use your special bite that will curse a villager instead of"
        " killing and devouring them. The cursed villager will then partake each night"
        " in the Werewolves' feast."
    ),
    Role.PARAGON: _(
        "You are the Paragon who has the ability to nullify all other nominations"
        " during the daily election. When you nominate one or more players, only those"
        " players will be voted for during the voting phase removing all other"
        " nominations."
    ),
    Role.RAIDER: _(
        "You're a lone Raider. As a Raider, you can loot a dead player and take their"
        " role as yours. However, only those who died last night and recently lynched"
        " players will be available for you to raid."
    ),
    Role.RITUALIST: _(
        "You are the Ritualist who can resurrect a Villager once per game."
    ),
    Role.TROUBLEMAKER: _(
        "You are the Troublemaker of the Village. You can exchange the roles of two"
        " other players on the first night."
    ),
    Role.LAWYER: _(
        "You are the Lawyer who can help the village stop their wrong decisions by"
        " objecting the nomination process and end the day without proceeding to any"
        ' voting phase. Just raise the powerful "Objection!" protest to use your'
        " ability once per game. (The exclamation point is optional.)"
    ),
    Role.WAR_VETERAN: _(
        "You're a War Veteran. Your past warfare has carried you through the duration"
        " of your life. Upon being lynched by the village's vote, you will randomly"
        " kill one of them as a form of your betrayal."
    ),
    Role.WOLF_SHAMAN: _(
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill together with them."
        " Additionally, you have the ability to summon an ancient werewolf spirit that"
        " will guard and protect a fellow werewolf to block one death."
    ),
    Role.WOLF_NECROMANCER: _(
        "Your objective is to kill all villagers together with the other Werewolves."
        " Every night, you will get to choose one villager to kill together with them."
        " Since you have learned from your shape-shifting ancestors the magic of"
        " summoning the dead, you have the ability to resurrect a dead werewolf at"
        " night once per game."
    ),
}


class Game:
    def __init__(
        self, ctx: Context, players: List[discord.Member], mode: str, speed: str
    ) -> None:
        self.ctx = ctx
        self.mode = mode
        self.speed = speed
        self.timers = {"Extended": 90, "Normal": 60, "Fast": 45, "Blitz": 30}
        self.timer = self.timers.get(self.speed, 60)
        self.game_link = _("Shortcut back to {ww_channel}").format(
            ww_channel=self.ctx.channel.mention
        )
        self.winning_team = None
        self.judge_spoken = False
        self.judge_symbol = None
        self.ex_maid = None
        self.rusty_sword_disease_night = None
        self.recent_deaths = []
        self.lovers = []
        self.available_roles = get_roles(len(players), self.mode)
        self.available_roles, self.extra_roles = (
            self.available_roles[:-2],
            self.available_roles[-2:],
        )

        if self.mode == "Huntergame":
            # Replace all non-Werewolf to Hunters
            for idx, role in enumerate(self.available_roles):
                if role not in [Role.WEREWOLF, Role.WHITE_WOLF, Role.BIG_BAD_WOLF]:
                    self.available_roles[idx] = Role.HUNTER
        elif self.mode == "Villagergame":
            # Replace all non-Werewolf to Villagers
            for idx, role in enumerate(self.available_roles):
                if role not in [Role.WEREWOLF, Role.WHITE_WOLF, Role.BIG_BAD_WOLF]:
                    self.available_roles[idx] = Role.VILLAGER

        if roles := force_role(self, Role.WEREWOLF):
            self.available_roles, self.extra_roles = roles
        self.players: List[Player] = [
            Player(role, user, self)
            for role, user in zip(self.available_roles, players)
        ]

        if self.mode == "Valentines":
            lovers = list(chunks(random.shuffle(self.players), 2))
            for couple in lovers:
                if len(couple) == 2:
                    self.lovers.append(set(couple))
        random.choice(self.players).is_sheriff = True

    @property
    def sheriff(self) -> Player:
        return discord.utils.get(self.alive_players, is_sheriff=True)

    @property
    def alive_players(self) -> List[Player]:
        return [player for player in self.players if not player.dead]

    @property
    def dead_players(self) -> List[Player]:
        return [player for player in self.players if player.dead]

    def get_role_name(self, player_or_role: Union[Player, Role]) -> str:
        role_name = ""
        if isinstance(player_or_role, Role):
            role = player_or_role
        elif isinstance(player_or_role, Player):
            role = player_or_role.role
            if player_or_role.cursed and role != Role.WEREWOLF:
                role_name = "Cursed "
        else:
            raise TypeError("Wrong type: player_or_role. Only Player or Role allowed")
        role_name += role.name.title().replace("_", " ")
        return role_name

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
                return _("No one")

    @property
    def new_afk_players(self) -> List[Player]:
        return [player for player in self.alive_players if player.to_check_afk]

    async def wolves(self) -> Optional[Player]:
        if healer := self.get_player_with_role(Role.HEALER):
            await healer.set_healer_target()
        wolves = [
            p
            for p in self.alive_players
            if p.side == Side.WOLVES or p.side == Side.WHITE_WOLF
        ]
        if len(wolves) == 0:
            return
        wolves_users = [str(p.user.id) for p in wolves]
        await self.ctx.send(_("**The Werewolves awake...**"))
        # Get target of wolves
        target_list = [p for p in self.alive_players if p not in wolves]
        possible_targets = {idx: p for idx, p in enumerate(target_list, 1)}
        fmt = commands.Paginator(prefix="", suffix="")
        wolf_names = _("Hey **")
        for player in wolves:
            if len(wolf_names + str(player.user) + ", ") > 1900:
                fmt.add_line(wolf_names + "**")
                wolf_names = "**"
            wolf_names += str(player.user) + ", "
            if player == wolves[-1]:
                fmt.add_line(wolf_names[:-2] + "**")
        if len(wolves) > 1:
            greet_text = _("__{count}__ Werewolves").format(count=len(wolves))
        else:
            greet_text = _("lone Werewolf")
        fmt.add_line(
            _("**🐺 Wake up {greet_text}! It is time to choose a victim**").format(
                greet_text=greet_text
            )
        )
        fmt.add_line(_("All possible victims are:"))
        for idx, p in possible_targets.items():
            fmt.add_line(
                f"{idx}. {p.user}"
                f" {p.user.mention} {p.role_name if p.role == Role.PURE_SOUL else ''}"
            )
        fmt.add_line("")
        fmt.add_line(
            _(
                "**I will relay all messages you send to the other Werewolves. Send a"
                " number to nominate them for killing (you can nominate up to 10"
                " users), voting starts in {timer} seconds.**"
            ).format(timer=self.timer)
        )
        fmt.add_line(
            _(
                "**Please do not spam and talk slowly! Relaying can take a while if"
                " there are many Werewolves!**"
            )
        )
        for user in wolves:
            for page in fmt.pages:
                await user.send(page)
        nominated = []
        try:
            async with timeout(self.timer):
                while len(nominated) < 10:
                    channels_ids = [
                        str(p.user.dm_channel.id)
                        for p in wolves
                        if p.user.dm_channel is not None
                    ]
                    msg = await self.ctx.bot.wait_for_dms(
                        "message",
                        check={
                            "author": {"id": wolves_users},
                            "channel_id": channels_ids,
                        },
                    )
                    if msg.content.isdigit() and int(msg.content) in possible_targets:
                        werewolf = discord.utils.get(
                            self.alive_players, user=msg.author
                        )
                        submitted_target = possible_targets[int(msg.content)]
                        if submitted_target in werewolf.own_lovers:
                            await werewolf.send(_("❌ You cannot nominate your Lover."))
                            continue
                        nominated.append(possible_targets[int(msg.content)])
                        text = _("**{werewolf}** nominated **{victim}**").format(
                            werewolf=msg.author, victim=nominated[-1].user
                        )
                    else:
                        text = f"**{msg.author}**: {msg.content}"
                    for user in wolves:
                        await user.send(text)
        except asyncio.TimeoutError:
            pass
        if not nominated:
            for user in wolves:
                await user.send(
                    _(
                        "Not a single one of you wanted to attack a villager. No fresh"
                        " meat tonight 😆.\n{game_link}"
                    ).format(game_link=self.game_link)
                )
            return
        nominated = {u: 0 for u in nominated}
        nominated_users_text = [str(u.user) + _(" Votes: {votes}") for u in nominated]
        nominated_users = [text.format(votes=0) for text in nominated_users_text]
        if len(nominated) > 1:
            for werewolf in wolves:
                await werewolf.send(
                    _("The voting is starting, please wait for your turn...")
                )
            done_voting = {w: False for w in wolves}
            for werewolf in wolves:

                async def get_vote():
                    while not done_voting[werewolf]:
                        try:
                            target = await self.ctx.bot.paginator.Choose(
                                entries=nominated_users,
                                return_index=True,
                                title=(
                                    _(
                                        "React to vote for a target. You have {timer}"
                                        " seconds."
                                    ).format(timer=self.timer)
                                ),
                                timeout=self.timer,
                            ).paginate(self.ctx, location=werewolf.user)
                        except (
                            self.ctx.bot.paginator.NoChoice,
                            discord.Forbidden,
                            discord.HTTPException,
                        ):
                            await werewolf.send(_("You timed out and didn't vote."))
                            return None, None
                        else:
                            voted = list(nominated.keys())[target]
                            if voted in werewolf.own_lovers:
                                await werewolf.send(
                                    _("❌ You cannot vote for your Lover to die.")
                                )
                                continue
                            return voted, target

                done, pending = await asyncio.wait(
                    {get_vote(),},
                    timeout=self.timer,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                try:
                    done_voting[werewolf] = True
                    if len(done) > 0:
                        voted, target = done.pop().result()
                    else:
                        voted = None
                except asyncio.TimeoutError:
                    voted = None
                if voted:
                    nominated[voted] += 1
                    nominated_users[target] = nominated_users_text[target].format(
                        votes=nominated[voted]
                    )
            targets = sorted(list(nominated.keys()), key=lambda x: -nominated[x])
            if nominated[targets[0]] > nominated[targets[1]]:
                target = targets[0]
            else:
                target = None
                for user in wolves:
                    await user.send(
                        _(
                            "Werewolves, you are all indecisive. No fresh meat tonight"
                            " 😆.\n{game_link}"
                        ).format(game_link=self.game_link)
                    )
        else:
            target = list(nominated.keys())[0]
        if target:
            for user in wolves:
                await user.send(
                    _(
                        "Werewolves, you have decided to kill **{target}** tonight"
                        " and be your meal.\n{game_link}"
                    ).format(target=target.user, game_link=self.game_link)
                )
            if cursed_wolf_father := self.get_player_with_role(Role.CURSED_WOLF_FATHER):
                target = await cursed_wolf_father.infect_target(target)
        await asyncio.sleep(5)  # Give them time to read
        return target

    async def announce_pure_soul(self, pure_soul: Player) -> None:
        for p in self.players:
            p.revealed_roles.update({pure_soul: pure_soul.role})
        await self.ctx.send(
            _("{pure_soul} is a **{role}** and an innocent villager.").format(
                pure_soul=pure_soul.user.mention, role=pure_soul.role_name
            )
        )

    async def announce_sheriff(self) -> None:
        await self.ctx.send(
            _(
                "📢 {sheriff} got randomly chosen as the new 🎖 **Sheriff**️. **The vote"
                " of the Sheriff counts as double.**"
            ).format(sheriff=self.sheriff.user.mention)
        )
        await self.dm_sheriff_info()

    async def dm_sheriff_info(self) -> None:
        await self.sheriff.send(
            _(
                "You became the 🎖 **Sheriff. Your vote counts as double. If you died or"
                " exchanged roles using Maid's ability, you must choose a new"
                " Sheriff.**"
            )
        )

    async def send_love_msgs(self) -> None:
        for couple in self.lovers:
            couple = list(couple)
            for lover in couple:
                await lover.send_love_msg(
                    couple[couple.index(lover) - 1], mode_effect=True
                )

    def get_chained_lovers(self, start: Player, chained: set = None) -> set:
        if chained is None:
            if len(start.own_lovers) == 0:
                return set()
            chained = set([start])
        others = set(start.own_lovers) - chained
        if len(others) == 0:
            return chained
        chained = chained.union(others)
        for lover in others:
            chained = self.get_chained_lovers(lover, chained)
        return chained

    async def initial_preparation(self) -> List[Player]:
        mode_emojis = {"Huntergame": "🔫", "Valentines": "💕"}
        mode_emoji = mode_emojis.get(self.mode, "")
        paginator = commands.Paginator(prefix="", suffix="")
        paginator.add_line(
            _("**The __{num}__ inhabitants of the Village:**").format(
                num=len(self.players)
            )
        )
        players = ""
        for player in self.players:
            if len(players + player.user.mention + " ") > 1900:
                paginator.add_line(players)
                players = ""
            players += player.user.mention + " "
            if player == self.players[-1]:
                paginator.add_line(players[:-1])
        paginator.add_line(
            _(
                "**Welcome to Werewolf {mode}!\n{speed} speed activated - All action"
                " timers are limited to {timer} seconds.**"
            ).format(
                mode=mode_emoji + self.mode + mode_emoji,
                speed=self.speed,
                timer=self.timer,
            )
        )
        for page in paginator.pages:
            await self.ctx.send(page)
        house_rules = _(
            "📜⚠️ Talking to other users privately is"
            " prohibited! Posting any screenshots of my messages"
            " containing your role is also forbidden."
        )
        await self.ctx.send(
            _(
                "**Sending game roles... You may use `{prefix}ww myrole` to check"
                " your role later.\n{house_rules}**"
            ).format(prefix=self.ctx.prefix, house_rules=house_rules)
        )
        for player in self.players:
            await player.send(
                _("**Welcome to Werewolf {mode}! {house_rules}\n{game_link}**").format(
                    mode=mode_emoji + self.mode + mode_emoji,
                    house_rules=house_rules,
                    game_link=self.game_link,
                )
            )
            await player.send_information()
        await self.announce_sheriff()
        await self.ctx.send(_("🌘 💤 **Night falls, the town is asleep...**"))
        await self.send_love_msgs()  # Send to lovers used on Valentines mode
        if thief := self.get_player_with_role(Role.THIEF):
            await thief.choose_thief_role()
        if wolfhound := self.get_player_with_role(Role.WOLFHOUND):
            await wolfhound.choose_wolfhound_role([Role.VILLAGER, Role.WEREWOLF])
        if amor := self.get_player_with_role(Role.AMOR):
            await amor.choose_lovers()
        if pure_soul := self.get_player_with_role(Role.PURE_SOUL):
            await self.announce_pure_soul(pure_soul)
        if seer := self.get_player_with_role(Role.SEER):
            await seer.check_player_card()
        if fox := self.get_player_with_role(Role.FOX):
            await fox.check_3_werewolves()
        if judge := self.get_player_with_role(Role.JUDGE):
            await judge.get_judge_symbol()
        if sisters := self.get_players_with_role(Role.SISTER):
            await self.ctx.send(_("**The Sisters awake...**"))
            for player in sisters:
                await player.send_family_msg("sister", sisters)
        if brothers := self.get_players_with_role(Role.BROTHER):
            await self.ctx.send(_("**The Brothers awake...**"))
            for player in brothers:
                await player.send_family_msg("brother", brothers)
        if troublemaker := self.get_player_with_role(Role.TROUBLEMAKER):
            await troublemaker.choose_2_to_exchange()
        if wild_child := self.get_player_with_role(Role.WILD_CHILD):
            await wild_child.choose_idol()
        target = await self.wolves()
        targets = [target] if target is not None else []
        if (
            sum(
                1
                for player in self.players
                if player.dead
                and (player.role == Role.WEREWOLF or player.role == Role.WILD_CHILD)
            )
            == 0
        ):
            if big_bad_wolf := self.get_player_with_role(Role.BIG_BAD_WOLF):
                if target := await big_bad_wolf.choose_villager_to_kill(targets):
                    targets.append(target)
        if wolf_shaman := self.get_player_with_role(Role.WOLF_SHAMAN):
            await wolf_shaman.protect_werewolf()
        if protected := discord.utils.get(self.alive_players, is_protected=True):
            protected.is_protected = False
            if protected in targets:
                targets.remove(protected)
        if knight := discord.utils.get(targets, role=Role.KNIGHT):
            knight.attacked_by_the_pact = True
        if witch := self.get_player_with_role(Role.WITCH):
            targets = await witch.witch_actions(targets)
        if flutist := self.get_player_with_role(Role.FLUTIST):
            await flutist.enchant()
        return targets

    async def night(self, white_wolf_ability: bool) -> List[Player]:
        moon = "🌕" if white_wolf_ability else "🌘"
        await self.ctx.send(moon + _(" 💤 **Night falls, the town is asleep...**"))
        if self.ex_maid and self.ex_maid.dead:
            self.ex_maid = None
        elif self.ex_maid:
            # Call ex-maid's new role like it's the first night
            if self.ex_maid.role == Role.THIEF:
                await self.ex_maid.choose_thief_role()
            if self.ex_maid.role == Role.WOLFHOUND:
                await self.ex_maid.choose_wolfhound_role([Role.VILLAGER, Role.WEREWOLF])
            elif self.ex_maid.role == Role.AMOR:
                await self.ex_maid.choose_lovers()
            elif self.ex_maid.role == Role.PURE_SOUL:
                await self.announce_pure_soul(self.ex_maid)
            elif self.ex_maid.role == Role.TROUBLEMAKER:
                await self.ex_maid.choose_2_to_exchange()
            elif self.ex_maid.role == Role.WILD_CHILD:
                await self.ex_maid.choose_idol()
            elif self.ex_maid.role == Role.JUDGE:
                await self.ex_maid.get_judge_symbol()
            elif self.ex_maid.role == Role.SISTER:
                sisters = self.get_players_with_role(Role.SISTER)
                for player in sisters:
                    if player == self.ex_maid:
                        continue
                    await player.send_family_member_msg("sister", self.ex_maid)
            elif self.ex_maid.role == Role.BROTHER:
                brothers = self.get_players_with_role(Role.BROTHER)
                for player in brothers:
                    if player == self.ex_maid:
                        continue
                    await player.send_family_member_msg("brother", self.ex_maid)
            self.ex_maid = None
        if ritualist := self.get_player_with_role(Role.RITUALIST):
            await ritualist.resurrect()
        if wolf_necro := self.get_player_with_role(Role.WOLF_NECROMANCER):
            await wolf_necro.resurrect_werewolf()
        if raider := self.get_player_with_role(Role.RAIDER):
            await raider.choose_to_raid()
        if seer := self.get_player_with_role(Role.SEER):
            await seer.check_player_card()
        if fox := self.get_player_with_role(Role.FOX):
            await fox.check_3_werewolves()
        target = await self.wolves()
        targets = [target] if target is not None else []
        if white_wolf_ability:
            if white_wolf := self.get_player_with_role(Role.WHITE_WOLF):
                target = await white_wolf.choose_werewolf()
                if target:
                    targets.append(target)
        if (
            sum(
                1
                for player in self.players
                if player.dead
                and (player.role == Role.WEREWOLF or player.role == Role.WILD_CHILD)
            )
            == 0
        ):
            if big_bad_wolf := self.get_player_with_role(Role.BIG_BAD_WOLF):
                if target := await big_bad_wolf.choose_villager_to_kill(targets):
                    targets.append(target)
        if wolf_shaman := self.get_player_with_role(Role.WOLF_SHAMAN):
            await wolf_shaman.protect_werewolf()
        if protected := discord.utils.get(self.alive_players, is_protected=True):
            protected.is_protected = False
            if protected in targets:
                targets.remove(protected)
        if knight := discord.utils.get(targets, role=Role.KNIGHT):
            knight.attacked_by_the_pact = True
        if witch := self.get_player_with_role(Role.WITCH):
            targets = await witch.witch_actions(targets)
        if flutist := self.get_player_with_role(Role.FLUTIST):
            await flutist.enchant()
        return targets

    async def election(self) -> Optional[discord.Member]:
        paginator = commands.Paginator(prefix="", suffix="")
        players = ""
        eligible_players_lines = []
        for player in self.alive_players:
            if len(players + player.user.mention + " ") > 1900:
                paginator.add_line(players)
                eligible_players_lines.append(players)
                players = ""
            players += player.user.mention + " "
            if player == self.alive_players[-1]:
                paginator.add_line(players[:-1])
                eligible_players_lines.append(players[:-1])
        paginator.add_line(
            _(
                "You may now submit someone (up to 10 total) for the election who to"
                " lynch by mentioning their name below. You have {timer} seconds of"
                " discussion during this time."
            ).format(timer=self.timer)
        )
        for page in paginator.pages:
            await self.ctx.send(page)
        nominated_by_paragon = []
        nominated = []
        second_election = False
        eligible_players = [player.user for player in self.alive_players]
        try:
            async with timeout(self.timer) as cm:
                start = datetime.datetime.utcnow()
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
                            or ("objection" in x.content.lower())
                        ),
                    )
                    if "objection" in msg.content.lower() and discord.utils.get(
                        self.alive_players,
                        role=Role.LAWYER,
                        user=msg.author,
                        has_objected=False,
                    ):
                        lawyer = self.get_player_with_role(Role.LAWYER)
                        lawyer.has_objected = True
                        await self.ctx.send(
                            _(
                                "**OBJECTION!!!** the **{role}** {user} protested."
                                " Nomination ends."
                            ).format(role=lawyer.role_name, user=lawyer.user.mention)
                        )
                        nominated_by_paragon.clear()
                        nominated.clear()
                        raise asyncio.TimeoutError()
                    if msg.content == self.judge_symbol and discord.utils.get(
                        self.alive_players, role=Role.JUDGE, user=msg.author
                    ):
                        second_election = True
                        self.judge_spoken = True
                        judge = self.get_player_with_role(Role.JUDGE)
                        await judge.send(
                            _(
                                "I received your secret phrase. We will hold another"
                                " election after this."
                            )
                        )
                    for user in msg.mentions:
                        if (
                            user in eligible_players
                            and user not in nominated
                            and len(nominated) < 10
                        ):
                            if discord.utils.get(
                                self.alive_players, role=Role.PARAGON, user=msg.author
                            ):
                                nominated_by_paragon.append(user)
                            nominated.append(user)
                            if len(nominated) == 1:
                                # Seems sneaky, extend talk time when there's only 10 seconds left
                                mention_time = datetime.datetime.utcnow()
                                if (mention_time - start) >= datetime.timedelta(
                                    seconds=self.timer - 10
                                ):
                                    time_to_add = int(self.timer / 2)
                                    cm.shift_by(time_to_add)
                                    await self.ctx.send(
                                        _(
                                            "Seems sneaky, I added {time_to_add}"
                                            " seconds talk time."
                                        ).format(time_to_add=time_to_add)
                                    )
                            await self.ctx.send(
                                _("**{player}** nominated **{nominee}**.").format(
                                    player=msg.author, nominee=user
                                )
                            )
        except asyncio.TimeoutError:
            pass
        if len(nominated_by_paragon) > 0:
            nominated = nominated_by_paragon
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
        paginator.clear()
        for line in eligible_players_lines:
            paginator.add_line(line)
        paginator.add_line(
            _(
                "**React to vote for killing someone. You have {timer} seconds"
                ".**\n{texts}"
            ).format(timer=self.timer, texts=texts)
        )
        for page in paginator.pages:
            msg = await self.ctx.send(page)
        for emoji in emojis:
            await msg.add_reaction(emoji)
        # Check for nuisance voters twice, first at half of action timer, and lastly just before counting votes
        await self.check_nuisances(msg, eligible_players, emojis, repeat=2)
        msg = await self.ctx.channel.fetch_message(msg.id)
        nominated = {u: 0 for u in nominated}
        mapping = {emoji: user for emoji, user in zip(emojis, nominated)}
        voters = []
        for reaction in msg.reactions:
            if str(reaction.emoji) in emojis:
                nominated[mapping[str(reaction.emoji)]] = sum(
                    [
                        2
                        if self.alive_players[eligible_players.index(user)].is_sheriff
                        else 1
                        async for user in reaction.users()
                        if user in eligible_players
                    ]
                )
                voters += [
                    user
                    async for user in reaction.users()
                    if user in eligible_players and user not in voters
                ]
        failed_voters = set(eligible_players) - set(voters)
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

    async def check_nuisances(self, msg, eligible_players, emojis, repeat: int) -> None:
        for i in range(repeat):
            await asyncio.sleep(int(self.timer / repeat))
            msg = await self.ctx.channel.fetch_message(msg.id)
            nuisance_voters = set()
            is_lacking_permission = None
            for reaction in msg.reactions:
                if str(reaction.emoji) in emojis:
                    nuisance_users = [
                        user
                        async for user in reaction.users()
                        if user not in eligible_players and user != self.ctx.me
                    ]
                    nuisance_voters.update(nuisance_users)
                    for to_remove in nuisance_users:
                        try:
                            await msg.remove_reaction(reaction.emoji, to_remove)
                        except discord.Forbidden:
                            is_lacking_permission = True
                            continue
                        except Exception as e:
                            self.ctx.send(_("An unexpected error occurred."))
                            raise e
            if len(nuisance_voters):
                paginator = commands.Paginator(prefix="", suffix="")
                for nuisance_voter in nuisance_voters:
                    paginator.add_line(nuisance_voter.mention)
                paginator.add_line(
                    _(
                        "**You should not vote since you're not in the game. Please do"
                        " not try to influence the game by voting unnecessarily. I will"
                        " remove your reactions.**"
                    )
                )
                if is_lacking_permission:
                    paginator.add_line(
                        _(
                            "**{author} I couldn't remove reactions. Please give me the"
                            " proper permissions to remove reactions.**"
                        ).format(author=self.ctx.author.mention)
                    )
                for page in paginator.pages:
                    await self.ctx.send(page)

    async def handle_afk(self) -> None:
        if self.winner() is not None:
            return
        if len(self.new_afk_players) < 1:
            return
        await self.ctx.send(
            _(
                "Checking AFK players if they're still in the game... Should be done in"
                " {timer} seconds."
            ).format(timer=self.timer)
        )
        afk_users_id = []
        for afk_player in self.new_afk_players:
            afk_users_id.append(str(afk_player.user.id))
            await afk_player.send(
                _(
                    "You failed to vote. This is just an AFK check:\n**Send any message"
                    " until I acknowledged that you're not AFK. You have {timer}"
                    " seconds.**"
                ).format(timer=self.timer)
            )
        not_afk = []
        try:
            async with timeout(self.timer):
                channels_ids = [
                    str(p.user.dm_channel.id)
                    for p in self.new_afk_players
                    if p.user.dm_channel is not None
                ]
                while len(not_afk) < len(self.new_afk_players):
                    msg = await self.ctx.bot.wait_for_dms(
                        "message",
                        check={
                            "author": {"id": afk_users_id},
                            "channel_id": channels_ids,
                        },
                    )
                    if msg.author.id not in not_afk:
                        not_afk.append(msg.author.id)
                        afk_users_id.remove(str(msg.author.id))
                        channels_ids.remove(str(msg.channel.id))
                        await msg.author.send(
                            _(
                                "☑️ You're not AFK. You can stop sending"
                                " message now.\n{game_link}"
                            ).format(game_link=self.game_link)
                        )
        except asyncio.TimeoutError:
            pass

        afk_players_to_kill = []
        for afk_player in self.new_afk_players:
            afk_player.to_check_afk = False
            if afk_player.user.id not in not_afk:
                afk_player.afk_strikes += 1
                if afk_player.afk_strikes >= 3:
                    if not afk_player.dead:
                        await afk_player.send(
                            _(
                                "**Strike 3!** You will now be killed by the game for"
                                " having 3 strikes of being AFK. Goodbye!"
                            )
                        )
                        afk_players_to_kill.append(afk_player)
                else:
                    await afk_player.send(
                        _(
                            "⚠️ **Strike {strikes}!** You have been"
                            " marked as AFK. __You'll be killed after 3 strikes.__"
                        ).format(strikes=afk_player.afk_strikes)
                    )
        for afk_player in afk_players_to_kill:
            await self.ctx.send(
                _(
                    "**{afk_player}** has been killed by"
                    " the game due to having 3 strikes of AFK."
                ).format(afk_player=afk_player.user.mention)
            )
            await afk_player.kill()

    async def handle_lynching(self, to_kill: discord.Member) -> None:
        await self.ctx.send(
            _("The community has decided to kill {to_kill}.").format(
                to_kill=to_kill.mention
            )
        )
        to_kill = discord.utils.get(self.alive_players, user=to_kill)
        # Handle maid here
        if maid := self.get_player_with_role(Role.MAID):
            if maid != to_kill:
                if to_kill.lives == 1 or to_kill.role == Role.THE_OLD:
                    await maid.handle_maid(to_kill)
        if to_kill.role in [Role.THE_OLD, Role.WAR_VETERAN]:
            to_kill.died_from_villagers = True
            to_kill.lives = 1
        await to_kill.kill()

    async def handle_rusty_sword_effect(self) -> None:
        possible_werewolves = [
            p for p in self.alive_players if p.side in (Side.WOLVES, Side.WHITE_WOLF)
        ]
        to_die = random.choice(possible_werewolves)
        await self.ctx.send(
            _(
                "{to_die} died from the disease caused by the Knight's rusty sword."
            ).format(to_die=to_die.user.mention)
        )
        self.rusty_sword_disease_night = None
        await to_die.kill()

    async def day(self, deaths: List[Player]) -> None:
        await self.ctx.send(_("🌤️ **The sun rises...**"))
        for death in deaths:
            await death.kill()
        if self.rusty_sword_disease_night is not None:
            if self.rusty_sword_disease_night == 0:
                self.rusty_sword_disease_night += 1
            elif self.rusty_sword_disease_night == 1:
                await self.handle_rusty_sword_effect()
        if len(self.alive_players) < 2:
            return
        if self.winner() is not None:
            return
        to_kill, second_election = await self.election()
        if to_kill is not None:
            await self.handle_lynching(to_kill)
        else:
            await self.ctx.send(_("Indecisively, the community has killed noone."))
        await self.handle_afk()
        if second_election:
            await self.ctx.send(
                _(
                    "📢 **The Judge used the secret phrase to hold another election to"
                    " lynch someone. The Judge's decision cannot be debated.**"
                )
            )
            to_kill, second_election = await self.election()
            if to_kill is not None:
                await self.handle_lynching(to_kill)
            else:
                await self.ctx.send(
                    _("Indecisively, the community has not lynched anyone.")
                )
            await self.handle_afk()

    async def run(self):
        # Handle thief etc and first night
        deaths = await self.initial_preparation()
        round_no = 1
        night_no = 1
        while True:
            if round_no % 2 == 1:
                if self.speed in ["Fast", "Blitz"]:
                    day_count = _("Day {day_count:.0f} of {days_limit}").format(
                        day_count=night_no, days_limit=len(self.players) + 3
                    )
                else:
                    day_count = _("Day {day_count:.0f}").format(day_count=night_no)
                await self.ctx.send(day_count)
                await self.day(deaths)
            else:
                night_no += 1
                deaths = await self.night(white_wolf_ability=night_no % 2 == 0)
                self.recent_deaths = []
            round_no += 1
            if self.speed in ["Fast", "Blitz"]:
                if round_no / 2 == len(self.players) + 3:
                    await self.ctx.send(
                        _(
                            "{day_count:.0f} days have already passed. Stopping game..."
                        ).format(day_count=round_no / 2)
                    )
                    break
            if self.winner() is not None:
                break

        winner = self.winner()
        results_pretext = _("Werewolf {mode} results:").format(mode=self.mode)
        if isinstance(winner, Player):
            if not self.winning_team:
                self.winning_team = winner.role_name
            paginator = commands.Paginator(prefix="", suffix="")
            paginator.add_line(
                _(
                    "{results_pretext} **The {winning_team} won!** 🎉 Congratulations:"
                ).format(
                    results_pretext=results_pretext, winning_team=self.winning_team
                )
            )
            winners = self.get_players_roles(has_won=True)
            for player in winners:
                paginator.add_line(player)
            for page in paginator.pages:
                await self.ctx.send(page)
            await self.reveal_others()
        elif winner is None:
            await self.ctx.send(
                _("{results_pretext} **No one won!**").format(
                    results_pretext=results_pretext
                )
            )
            await self.reveal_others()
        else:
            # Due to IndexError, no need to reveal players
            await self.ctx.send(
                _("{results_pretext} **{winner} won!**").format(
                    results_pretext=results_pretext, winner=winner
                )
            )

    def get_players_roles(self, has_won: bool = False) -> List[str]:
        if len(self.alive_players) < 1:
            return ""
        else:
            players_to_reveal = []
            for player in self.alive_players:
                if player.has_won == has_won:
                    if (
                        player.role != player.initial_roles[0]
                        or len(player.initial_roles) > 1
                    ):
                        initial_role_info = _(
                            " A **{initial_roles}** initially."
                        ).format(
                            initial_roles=", ".join(
                                [
                                    self.get_role_name(initial_role)
                                    for initial_role in player.initial_roles
                                ]
                            )
                        )
                    else:
                        initial_role_info = ""
                    players_to_reveal.append(
                        _("{player} is a **{role}**!{initial_role_info}").format(
                            player=player.user.mention,
                            role=self.get_role_name(player),
                            initial_role_info=initial_role_info,
                        )
                    )
            return players_to_reveal

    async def reveal_others(self) -> None:
        if len([p for p in self.alive_players if p.has_won is False]) < 1:
            return
        paginator = commands.Paginator(prefix="", suffix="")
        paginator.add_line(
            _("The game has ended. I will now reveal the other living players' roles:")
        )
        non_winners = self.get_players_roles(has_won=False)
        for non_winner in non_winners:
            paginator.add_line(non_winner)
        for page in paginator.pages:
            await self.ctx.send(page)


class Player:
    def __init__(self, role: Role, user: discord.Member, game: Game) -> None:
        self.role = role
        self.initial_roles = [role]
        self.user = user
        self.game = game
        self.is_sheriff = False
        self.enchanted = False
        self.idol = None
        self.is_protected = False
        self.cursed = False
        self.revealed_roles = {}

        # Witch
        self.can_heal = True
        self.can_kill = True

        # Healer
        self.last_target = None

        # Fox
        self.has_fox_ability = True

        # Maid
        self.exchanged_with_maid = False

        # The Old
        self.died_from_villagers = False
        if role == Role.THE_OLD:
            self.lives = 2
        else:
            self.lives = 1

        # Rusty Sword Knight
        self.attacked_by_the_pact = False

        # Cursed Wolf Father
        self.has_cursed_wolf_father_ability = True

        # Raider
        self.has_raided = False

        # Ritualist
        self.has_ritualist_ability = True

        # lawyer
        self.has_objected = False

        # Wolf Shaman
        self.has_wolf_shaman_ability = True

        # Wolf Necromancer
        self.has_wolf_necro_ability = True

        # AFK check
        self.afk_strikes = 0
        self.to_check_afk = False

    def __repr__(self):
        return (
            f"<Player role={self.role} initial_role={self.initial_roles}"
            f" is_sheriff={self.is_sheriff} lives={self.lives} side={self.side}"
            f" dead={self.dead} won={self.has_won}>"
        )

    async def send(self, *args, **kwargs) -> Optional[discord.Message]:
        try:
            return await self.user.send(*args, **kwargs)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def choose_users(
        self,
        title: str,
        list_of_users: List[Player],
        amount: int,
        required: bool = True,
    ) -> List[Player]:
        fmt = [
            f"{idx}. {p.user}"
            f" {p.user.mention}"
            f" {self.game.get_role_name(self.revealed_roles[p]) if p in self.revealed_roles else ''}"
            for idx, p in enumerate(list_of_users, 1)
        ]
        if not required:
            fmt.insert(0, "0. Dismiss")
            prompt_msg = _(
                "**Type the number of the user to choose for this action. Type `0` to"
                " dismiss. You need to choose {amount} more.**"
            )
            start_num = 0
        else:
            prompt_msg = _(
                "**Type the number of the user to choose for this action. You need to"
                " choose {amount} more.**"
            )
            start_num = 1
        paginator = commands.Paginator(prefix="", suffix="")
        paginator.add_line(f"**{title}**")
        for i in fmt:
            paginator.add_line(i)
        for page in paginator.pages:
            await self.send(page)
        mymsg = await self.send(prompt_msg.format(amount=amount))
        chosen = []
        while len(chosen) < amount:
            msg = await self.game.ctx.bot.wait_for_dms(
                "message",
                check={
                    "author": {"id": str(self.user.id)},
                    "content": [
                        str(i) for i in range(start_num, len(list_of_users) + 1)
                    ],
                },
                timeout=self.game.timer,
            )
            if int(msg.content) == 0 and not required:
                return []
            player = list_of_users[int(msg.content) - 1]
            if player in chosen:
                await self.send(
                    _("🚫 You've chosen **{player}** already.").format(
                        player=player.user
                    )
                )
                continue
            if amount > 1:
                await self.send(
                    _("**{player}** has been selected.").format(player=player.user)
                )
            chosen.append(player)
            await mymsg.edit(content=prompt_msg.format(amount=amount - len(chosen)))
        return chosen

    async def send_information(self) -> None:
        await self.send(
            _("You are a **{role}**\n\n{description}").format(
                role=self.role_name, description=DESCRIPTIONS[self.role]
            )
        )

    async def send_love_msg(self, lover: Player, mode_effect: bool = False) -> None:
        if mode_effect:
            love_msg = _(
                "It's 💕Valentines💕! You fell in love with **{lover}**!"
                " You can eliminate all others and survive as **Lovers**."
                " Try to protect your lover as best as you can. You will immediately"
                " commit suicide once they die. May the best Lovers win!\n{game_link}"
            ).format(lover=lover.user, game_link=self.game.game_link)
        else:
            love_msg = _(
                "💕 You fell in love with **{lover}**! 💘 Amor really knew you had an eye"
                " on them... You can eliminate all others and survive as **Lovers**."
                " Try to protect your lover as best as you can. You will immediately"
                " commit suicide once they die.\n{game_link}"
            ).format(lover=lover.user, game_link=self.game.game_link)
        await self.send(love_msg)

    async def choose_idol(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes and chooses its idol...**").format(
                role=self.role_name
            )
        )
        possible_idols = [p for p in self.game.alive_players if p != self]
        try:
            idol = await self.choose_users(
                _("Choose your Idol. You will turn into a Werewolf if they die."),
                list_of_users=possible_idols,
                amount=1,
                required=True,
            )
            idol = idol[0]
        except asyncio.TimeoutError:
            idol = random.choice(possible_idols)
            await self.send(
                _("You didn't choose anyone. A random player will be chosen for you.")
            )
        self.idol = idol
        await self.send(
            _("**{idol}** became your Idol.\n{game_link}").format(
                idol=self.idol.user, game_link=self.game.game_link
            )
        )

    async def get_judge_symbol(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        self.game.judge_spoken = False
        await self.send(
            _(
                "🧑‍⚖️ Please enter a phrase that will trigger a second election. Its is"
                " case sensitive."
            )
        )
        try:
            msg = await self.game.ctx.bot.wait_for_dms(
                "message",
                check={"author": {"id": str(self.user.id)}},
                timeout=self.game.timer,
            )
            symbol = msg.content
        except asyncio.TimeoutError:
            symbol = "hahayes"
        await self.send(
            _(
                "The phrase is **{symbol}**. Enter it right during an"
                " election to trigger another one.\n{game_link}"
            ).format(symbol=symbol, game_link=self.game.game_link)
        )
        self.game.judge_symbol = symbol

    async def handle_maid(self, death: Player) -> None:
        if self.in_love and death in self.own_lovers:
            return
        try:
            action = await self.game.ctx.bot.paginator.Choose(
                entries=["Yes", "No"],
                return_index=True,
                title=_(
                    "Would you like to swap roles with {dying_one}? You will learn"
                    " their role once you accept."
                ).format(dying_one=death.user),
                timeout=self.game.timer,
            ).paginate(self.game.ctx, location=self.user)
        except self.game.ctx.bot.paginator.NoChoice:
            await self.send(_("You didn't choose anything."))
            return
        except (discord.Forbidden, discord.HTTPException):
            await self.game.ctx.send(
                _(
                    "I couldn't send a DM to someone. Too bad they missed to use their"
                    " power."
                )
            )
            return
        if action == 1:
            return
        if Role.WOLFHOUND in death.initial_roles or death.role == Role.WOLFHOUND:
            role_to_get = Role.WOLFHOUND
        else:
            role_to_get = death.role
        if death.initial_roles[-1] != death.role:
            death.initial_roles.append(death.role)
        death.role = self.role
        if self.initial_roles[-1] != self.role:
            self.initial_roles.append(self.role)
        self.role = role_to_get
        if self.role == Role.THE_OLD:
            self.lives = 2
            death.lives = 1
        self.game.ex_maid = self
        death.exchanged_with_maid = True
        await self.send(
            _("Your new role is now **{new_role}**.\n").format(new_role=self.role_name)
        )
        await self.send_information()
        if self.enchanted:
            self.enchanted = False
            await self.send(
                _("You're no longer enchanted by the {flutist}.").format(
                    flutist=self.game.get_role_name(Role.FLUTIST)
                )
            )
        await self.game.ctx.send(
            _(
                "**{maid}** reveals themselves as the **{role}** and exchanged"
                " roles with {dying_one}."
            ).format(maid=self.user, role=death.role_name, dying_one=death.user.mention)
        )
        if self.is_sheriff:
            await self.choose_new_sheriff(exclude=death)
        await self.send(self.game.game_link)

    async def set_healer_target(self) -> Player:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        available = [
            player for player in self.game.alive_players if player != self.last_target
        ]
        self.last_target = None
        try:
            target = await self.choose_users(
                _("Choose a player to protect from Werewolves."),
                list_of_users=available,
                amount=1,
                required=False,
            )
            if target:
                target = target[0]
            else:
                await self.send(
                    _(
                        "You didn't choose to heal anyone. No one will be protected"
                        " from the werewolves tonight.\n{game_link}"
                    ).format(game_link=self.game.game_link)
                )
                return
        except asyncio.TimeoutError:
            await self.send(
                _(
                    "You didn't choose anyone, slowpoke. No one will be protected from"
                    " the werewolves tonight.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
            return
        self.last_target = target
        self.last_target.is_protected = True
        await self.send(
            _(
                "**{protected}** won't die from the werewolves tonight.\n{game_link}"
            ).format(protected=self.last_target.user, game_link=self.game.game_link)
        )

    async def choose_werewolf(self) -> Optional[Player]:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        possible_targets = [
            p
            for p in self.game.alive_players
            if p.side == Side.WOLVES and p not in self.own_lovers
        ]
        if len(possible_targets) < 1:
            await self.send(
                _("There's no other werewolf left to kill.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        else:
            try:
                target = await self.choose_users(
                    _("Choose a Werewolf to kill."),
                    list_of_users=possible_targets,
                    amount=1,
                    required=False,
                )
                if target:
                    target = target[0]
                else:
                    await self.send(
                        _(
                            "You didn't choose any werewolf to kill.\n{game_link}"
                        ).format(game_link=self.game.game_link)
                    )
                    return
            except asyncio.TimeoutError:
                await self.send(
                    _(
                        "You didn't choose any werewolf to kill, slowpoke.\n{game_link}"
                    ).format(game_link=self.game.game_link)
                )
                return
            await self.send(
                _("You chose to kill **{werewolf}**.\n{game_link}").format(
                    werewolf=target.user, game_link=self.game.game_link
                )
            )
            return target

    async def choose_villager_to_kill(self, targets: List[Player]) -> Player:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        possible_targets = [
            p
            for p in self.game.alive_players
            if p.side not in (Side.WOLVES, Side.WHITE_WOLF)
            and p not in targets + self.own_lovers
        ]
        if len(possible_targets) < 1:
            await self.send(
                _(
                    "There's no other possible villagers left to kill.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
            return
        else:
            try:
                target = await self.choose_users(
                    _("Choose a Villager to kill."),
                    list_of_users=possible_targets,
                    amount=1,
                    required=False,
                )
                if target:
                    target = target[0]
                else:
                    await self.send(
                        _(
                            "You didn't choose any villager to kill.\n{game_link}"
                        ).format(game_link=self.game.game_link)
                    )
                    return
            except asyncio.TimeoutError:
                await self.send(
                    _(
                        "You didn't choose any villager to kill, slowpoke.\n{game_link}"
                    ).format(game_link=self.game.game_link)
                )
                return
            await self.send(
                _("You've decided to kill **{villager}**.\n{game_link}").format(
                    villager=target.user, game_link=self.game.game_link
                )
            )
            return target

    async def witch_actions(self, targets: List[Player]) -> Player:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        if not self.can_heal and not self.can_kill:
            # Delay is given here so that the Witch will not be accused of using up all the abilities already
            await asyncio.sleep(random.randint(5, int(self.game.timer / 2)))
            return targets
        if any(targets) and self.can_heal:
            try:
                to_heal = await self.choose_users(
                    _(
                        "Choose someone to heal 🧪. You can rescue a player attacked by"
                        " the wolves once throughout the game. You can opt not to use"
                        " this ability for now."
                    ),
                    list_of_users=targets,
                    amount=1,
                    required=False,
                )
                if to_heal:
                    to_heal = to_heal[0]
                    targets.remove(to_heal)
                    self.can_heal = False
                    if to_heal.role == Role.KNIGHT:
                        to_heal.attacked_by_the_pact = False
                    await self.send(
                        _("You chose to heal **{healed}**.").format(healed=to_heal.user)
                    )
                else:
                    await self.send(_("You didn't choose to heal anyone."))
            except asyncio.TimeoutError:
                await self.send(
                    _(
                        "You didn't choose to heal anyone from the list, slowpoke."
                        " They're likely to die."
                    )
                )
        if self.can_kill:
            possible_targets = [
                p
                for p in self.game.alive_players
                if p != self and p not in targets + self.own_lovers
            ]
            try:
                to_kill = await self.choose_users(
                    _(
                        "Choose someone to poison ☠️. You can kill a"
                        " player once throughout the game. You can opt not to use this"
                        " ability for now."
                    ),
                    list_of_users=possible_targets,
                    amount=1,
                    required=False,
                )
                if to_kill:
                    to_kill = to_kill[0]
                    if to_kill.role == Role.THE_OLD:
                        # Bad choice
                        to_kill.died_from_villagers = True
                        to_kill.lives = 1
                    targets.append(to_kill)
                    self.can_kill = False
                    await self.send(
                        _("You've decided to poison **{poisoned}**.").format(
                            poisoned=to_kill.user
                        )
                    )
                else:
                    await self.send(_("You didn't choose to poison anyone."))
            except asyncio.TimeoutError:
                await self.send(
                    _("You've ran out of time and missed to poison anyone, slowpoke.")
                )
        else:
            # Delay is given here so that the Witch will not be accused of using up all the abilities already
            await asyncio.sleep(random.randint(5, int(self.game.timer / 2)))
            return targets
        await self.send(self.game.game_link)
        return targets

    async def enchant(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        possible_targets = [
            p
            for p in self.game.alive_players
            if not p.enchanted and p != self and p not in self.own_lovers
        ]
        if len(possible_targets) > 2:
            try:
                to_enchant = await self.choose_users(
                    _("Choose 2 people to enchant."),
                    list_of_users=possible_targets,
                    amount=2,
                    required=False,
                )
                if not to_enchant:
                    await self.send(
                        _("You didn't want to use your ability.\n{game_link}").format(
                            game_link=self.game.game_link
                        )
                    )
            except asyncio.TimeoutError:
                to_enchant = []
                await self.send(
                    _(
                        "You didn't choose enough players to enchant,"
                        " slowpoke.\n{game_link}"
                    ).format(game_link=self.game.game_link)
                )
                return
        else:
            await self.send(
                _(
                    "The last {count} possible targets have been"
                    " automatically enchanted for you."
                ).format(count=len(possible_targets))
            )
            to_enchant = possible_targets
        for p in to_enchant:
            p.enchanted = True
            await self.send(
                _("You have enchanted **{enchanted}**.").format(enchanted=p.user)
            )
            await p.send(
                _(
                    "You have been enchanted by the Flutist. Claim being enchanted to"
                    " narrow him down.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
        await self.send(self.game.game_link)

    async def send_family_msg(self, relationship: str, family: List[Player]) -> None:
        await self.send(
            _("Your {relationship}(s) are/is: {members}").format(
                relationship=relationship,
                members=" and ".join(["**" + str(u.user) + "**" for u in family]),
            )
        )

    async def send_family_member_msg(
        self, relationship: str, new_member: Player
    ) -> None:
        await self.send(
            _(
                "Your new {relationship} is: **{new_member}**. They don't know yet"
                " the other members of the family."
            ).form(relationship=relationship, new_member=new_member.user)
        )

    async def check_player_card(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        try:
            to_inspect = await self.choose_users(
                _("👁️ Choose someone whose identity you would like to see."),
                list_of_users=[u for u in self.game.alive_players if u != self],
                amount=1,
                required=False,
            )
            if to_inspect:
                to_inspect = to_inspect[0]
            else:
                await self.send(
                    _(
                        "You didn't want to use your ability to see anyone's"
                        " role.\n{game_link}"
                    ).format(game_link=self.game.game_link)
                )
                return
        except asyncio.TimeoutError:
            await self.send(
                _(
                    "You've ran out of time and missed to see someone's role,"
                    " slowpoke.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
            return
        self.revealed_roles.update({to_inspect: to_inspect.role})
        await self.send(
            _("**{player}** is a **{role}**.\n{game_link}").format(
                player=to_inspect.user,
                role=to_inspect.role_name,
                game_link=self.game.game_link,
            )
        )

    async def choose_thief_role(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        entries = [self.game.get_role_name(role) for role in self.game.extra_roles]
        await self.send(
            _(
                "You will be asked to choose a new role from these:\n**{choices}**"
            ).format(choices=", ".join(entries))
        )
        if entries[0] == entries[1] == "Werewolf":
            await self.send(
                _(
                    "But it seems you don't have a choice. Whether you choose or not,"
                    " you will become a Werewolf."
                )
            )
        else:
            entries.append(_("Choose nothing and stay as Thief."))
        try:
            choice = await self.game.ctx.bot.paginator.Choose(
                entries=entries,
                return_index=True,
                title=_("Choose a new role"),
                timeout=self.game.timer,
            ).paginate(self.game.ctx, location=self.user)
            if choice < 2:
                self.role = self.game.extra_roles[choice]
            else:
                await self.send(
                    _("You chose to stay as Thief.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
        except self.game.ctx.bot.paginator.NoChoice:
            await self.send(
                _(
                    "You didn't choose anything. You will stay as Thief.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
        except (discord.Forbidden, discord.HTTPException):
            if not (entries[0] == entries[1] == "Werewolf"):
                await self.game.ctx.send(
                    _("I couldn't send a DM to this player. They will stay as Thief.")
                )
                return
        if entries[0] == entries[1] == "Werewolf":
            self.role = Role.WEREWOLF
        if self.role != Role.THIEF:
            if self.initial_roles[-1] != Role.THIEF:
                self.initial_roles.append(Role.THIEF)
            if self.role == Role.THE_OLD:
                self.lives = 2
            await self.send(
                _("Your new role is now **{new_role}**.\n{game_link}").format(
                    new_role=self.role_name, game_link=self.game.game_link
                )
            )
            await self.send_information()

    async def choose_wolfhound_role(self, roles: List[Role]) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        entries = [self.game.get_role_name(role) for role in roles]
        await self.send(
            _(
                "You will be asked to choose a new role from these:\n**{choices}**"
            ).format(choices=", ".join(entries))
        )
        try:
            can_dm = True
            choice = await self.game.ctx.bot.paginator.Choose(
                entries=entries,
                return_index=True,
                title=_("Choose a new role"),
                timeout=self.game.timer,
            ).paginate(self.game.ctx, location=self.user)
            role = roles[choice]
        except self.game.ctx.bot.paginator.NoChoice:
            role = random.choice(roles)
            await self.send(
                _(
                    "You didn't choose anything. A random role was chosen for"
                    " you.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
        except (discord.Forbidden, discord.HTTPException):
            can_dm = False
            role = random.choice(roles)
            await self.game.ctx.send(
                _("I couldn't send a DM. A random role was chosen for them.")
            )
        if self.initial_roles[-1] != self.role:
            self.initial_roles.append(self.role)
        self.role = role
        if can_dm:
            await self.send(
                _("Your new role is now **{new_role}**.\n{game_link}").format(
                    new_role=self.role_name, game_link=self.game.game_link
                )
            )
            await self.send_information()
            await self.send()

    async def check_3_werewolves(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        if not self.has_fox_ability:
            # Delay is given here so that the Fox will not be accused of losing the ability already
            await asyncio.sleep(random.randint(5, int(self.game.timer / 2)))
            return
        possible_targets = [p for p in self.game.alive_players if p != self]
        if len(possible_targets) > 3:
            try:
                target = await self.choose_users(
                    _(
                        "🦊 Choose the center player of the group of 3 neighboring"
                        " players who you want to see if any of them is a"
                        " werewolf.\n__Note: The First and Last players in the list are"
                        " neighbors.__"
                    ),
                    list_of_users=[u for u in self.game.alive_players if u != self],
                    amount=1,
                    required=False,
                )
                if not target:
                    await self.send(
                        _("You didn't want to use your ability.\n{game_link}").format(
                            game_link=self.game.game_link
                        )
                    )
                    return
                else:
                    target = target[0]
            except asyncio.TimeoutError:
                await self.send(
                    _("You didn't choose a player, slowpoke.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
            idx = possible_targets.index(target)
            size = len(possible_targets)
            group = [
                possible_targets[(idx - 1) % size],
                target,
                possible_targets[(idx + 1) % size],
            ]
        else:
            group = possible_targets
            await self.send(
                _(
                    "The last {count} possible targets have been"
                    " automatically selected for you."
                ).format(count=len(possible_targets))
            )
        if not any([target.side in (Side.WOLVES, Side.WHITE_WOLF) for target in group]):
            self.has_fox_ability = False
            await self.send(
                _(
                    "You found no Werewolf so you lost your ability.\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
        else:
            await self.send(
                _("One of them is a Werewolf.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
        await asyncio.sleep(3)  # Give time to read

    async def choose_lovers(self) -> None:
        await self.game.ctx.send(
            _("**{role} awakes and shoots their arrows...**").format(
                role=self.role_name
            )
        )
        try:
            lovers = await self.choose_users(
                _(
                    "💘 Choose 2 lovers 💕. You should not tell the town who the lovers"
                    " are."
                ),
                list_of_users=self.game.alive_players,
                amount=2,
            )
        except asyncio.TimeoutError:
            await self.send(
                _("You've ran out of time, slowpoke. Lovers will be chosen randomly.")
            )
            lovers = random.sample(self.game.alive_players, 2)
        await self.send(
            _("You've made **{lover1}** and **{lover2}** lovers\n{game_link}").format(
                lover1=lovers[0].user,
                lover2=lovers[1].user,
                game_link=self.game.game_link,
            )
        )
        if lovers[0] not in lovers[1].own_lovers:
            self.game.lovers.append(
                set(lovers)
            )  # Add if they're not yet already lovers.
        await lovers[0].send_love_msg(lovers[1])
        await lovers[1].send_love_msg(lovers[0])

    async def choose_to_raid(self) -> None:
        if self.has_raided or len(self.game.recent_deaths) == 0:
            return
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        possible_targets = [p for p in self.game.recent_deaths]
        try:
            to_raid = await self.choose_users(
                _("Choose a dead player to raid and take their role."),
                list_of_users=possible_targets,
                amount=1,
                required=False,
            )
            if not to_raid:
                await self.send(
                    _("You didn't want to use your ability.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
        except asyncio.TimeoutError:
            await self.send(
                _("You've ran out of time, slowpoke.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        to_raid = to_raid[0]
        if self.initial_roles[-1] != self.role:
            self.initial_roles.append(self.role)
        self.role = to_raid.role
        self.has_raided = True
        await self.send(
            _(
                "You've raided **{to_raid}** to take their loots and their role. You're"
                " now a **{new_role}**.\n{game_link}"
            ).format(
                to_raid=to_raid.user,
                new_role=to_raid.role_name,
                game_link=self.game.game_link,
            )
        )
        await self.send_information()
        if self.role == Role.THIEF:
            await self.ex_maid.choose_thief_role()
        if self.role == Role.WOLFHOUND:
            await self.choose_wolfhound_role([Role.VILLAGER, Role.WEREWOLF])
        elif self.role == Role.AMOR:
            await self.choose_lovers()
        elif self.role == Role.PURE_SOUL:
            await self.announce_pure_soul(self)
        elif self.role == Role.TROUBLEMAKER:
            await self.choose_2_to_exchange()
        elif self.role == Role.WILD_CHILD:
            await self.choose_idol()
        elif self.role == Role.JUDGE:
            await self.get_judge_symbol()
        elif self.role == Role.SISTER:
            sisters = self.get_players_with_role(Role.SISTER)
            for player in sisters:
                if player == self:
                    continue
                await player.send_family_member_msg("sister", self)
        elif self.role == Role.BROTHER:
            brothers = self.get_players_with_role(Role.BROTHER)
            for player in brothers:
                if player == self:
                    continue
                await player.send_family_member_msg("brother", self)
        elif self.role == Role.THE_OLD:
            self.lives = 2

    async def resurrect(self) -> None:
        if not self.has_ritualist_ability:
            return
        dead_non_wolves = [
            p
            for p in self.game.dead_players
            if p.side != Side.WOLVES and p.side != Side.WHITE_WOLF
        ]
        if len(dead_non_wolves) == 0:
            return
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        try:
            to_resurrect = await self.choose_users(
                _("Choose a villager to resurrect."),
                list_of_users=dead_non_wolves,
                amount=1,
                required=False,
            )
            if not to_resurrect:
                await self.send(
                    _("You didn't want to use your ability.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
            else:
                to_resurrect = to_resurrect[0]
        except asyncio.TimeoutError:
            await self.send(
                _("You've ran out of time, slowpoke.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        to_resurrect.lives = 1 if to_resurrect.role != Role.THE_OLD else 2
        self.has_ritualist_ability = False
        await self.send(
            _(
                "You're trying to resurrect **{to_resurrect}** by performing series of"
                " rituals and prayers of ancient languages.\n{game_link}"
            ).format(to_resurrect=to_resurrect.user, game_link=self.game.game_link)
        )
        await self.game.ctx.send(
            _("{player} has been resurrected!").format(player=to_resurrect.user.mention)
        )
        await to_resurrect.send(
            _("You have been resurrected as **{role}!**.\n{game_link}").format(
                role=to_resurrect.role_name, game_link=self.game.game_link
            )
        )

    async def resurrect_werewolf(self) -> None:
        if not self.has_wolf_necro_ability:
            return
        dead_wolves = [
            p
            for p in self.game.dead_players
            if p.side == Side.WOLVES or p.side == Side.WHITE_WOLF
        ]
        if len(dead_wolves) == 0:
            return
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        try:
            to_resurrect = await self.choose_users(
                _("Choose a werewolf to resurrect."),
                list_of_users=dead_wolves,
                amount=1,
                required=False,
            )
            if not to_resurrect:
                await self.send(
                    _("You didn't want to use your ability.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
            else:
                to_resurrect = to_resurrect[0]
        except asyncio.TimeoutError:
            await self.send(
                _("You've ran out of time, slowpoke.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        to_resurrect.lives = 1
        self.has_wolf_necro_ability = False
        await self.send(
            _(
                "You used necromancy to bring **{to_resurrect}** back to"
                " life.\n{game_link}"
            ).format(to_resurrect=to_resurrect.user, game_link=self.game.game_link)
        )
        await self.game.ctx.send(
            _("**{player}** came back to life!").format(
                player=to_resurrect.user.mention
            )
        )
        await to_resurrect.send(
            _("You came back to life as **{role}!**\n{game_link}").format(
                role=self.game.get_role_name(to_resurrect),
                game_link=self.game.game_link,
            )
        )

    async def choose_2_to_exchange(self) -> None:
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        possible_targets = [p for p in self.game.alive_players if p != self]
        try:
            exchanged = await self.choose_users(
                _("Choose 2 players that will exchange their roles with each other."),
                list_of_users=possible_targets,
                amount=2,
                required=False,
            )
            if not exchanged:
                await self.send(
                    _("You didn't want to use your ability.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
        except asyncio.TimeoutError:
            await self.send(
                _("You've ran out of time, slowpoke.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        role = exchanged[0].role
        if exchanged[0].initial_roles[-1] != exchanged[0].role:
            exchanged[0].initial_roles.append(exchanged[0].role)
        exchanged[0].role = exchanged[1].role
        if exchanged[1].initial_roles[-1] != exchanged[1].role:
            exchanged[1].initial_roles.append(exchanged[1].role)
        exchanged[1].role = role
        exchanged[0].lives, exchanged[1].lives = exchanged[1].lives, exchanged[0].lives
        await self.send(
            _(
                "You've exchanged **{exchange1}'s** and **{exchange2}'s** roles with"
                " each other.\n{game_link}"
            ).format(
                exchange1=exchanged[0].user,
                exchange2=exchanged[1].user,
                game_link=self.game.game_link,
            )
        )
        await exchanged[0].send(
            _(
                "The **{troublemaker}** exchanged your role with someone. You are now a"
                " **{new_role}**.\n{game_link}"
            ).format(
                troublemaker=self.role_name,
                new_role=exchanged[0].role_name,
                game_link=self.game.game_link,
            )
        )
        await exchanged[0].send_information()
        await exchanged[1].send(
            _(
                "The **{troublemaker}** exchanged your role with someone. You are now a"
                " **{new_role}**.\n{game_link}"
            ).format(
                troublemaker=self.role_name,
                new_role=exchanged[1].role_name,
                game_link=self.game.game_link,
            )
        )
        await exchanged[1].send_information()

    async def protect_werewolf(self) -> None:
        if not self.has_wolf_shaman_ability:
            return
        await self.game.ctx.send(
            _("**The {role} awakes...**").format(role=self.role_name)
        )
        wolves = [
            p
            for p in self.game.alive_players
            if p.side == Side.WOLVES or p.side == Side.WHITE_WOLF
        ]
        try:
            protected = await self.choose_users(
                _(
                    "Choose a Werewolf to send a spiritual protection to block death"
                    " for one time."
                ),
                list_of_users=wolves,
                amount=1,
                required=False,
            )
            if protected:
                protected = protected[0]
            else:
                await self.send(
                    _("You didn't want to use your ability.\n{game_link}").format(
                        game_link=self.game.game_link
                    )
                )
                return
        except asyncio.TimeoutError:
            await self.send(
                _("You didn't choose anyone, slowpoke.\n{game_link}").format(
                    game_link=self.game.game_link
                )
            )
            return
        protected.lives = 2
        self.has_wolf_shaman_ability = False
        await self.send(
            _(
                "**{protected}** is now protected to block one death.\n{game_link}"
            ).format(protected=protected.user, game_link=self.game.game_link)
        )
        if protected != self:
            await protected.send(
                _(
                    "The **{role}** sent you a spiritual protection to block one"
                    " death.\n{game_link}"
                ).format(role=self.role_name, game_link=self.game.game_link)
            )

    async def infect_target(self, target: Player) -> None:
        if not self.has_cursed_wolf_father_ability or discord.utils.get(
            self.game.players, cursed=True
        ):
            return target
        # This one's commented out as we want Cursed Wolf Father infects someone secretly
        # await self.game.ctx.send(_("**The {role} awakes...**").format(role=self.role_name))
        try:
            action = await self.game.ctx.bot.paginator.Choose(
                entries=["Yes", "No"],
                return_index=True,
                title=_(
                    "Would you like to infect **{target}** with your curse to join your"
                    " nightly killings?"
                ).format(target=target.user),
                timeout=self.game.timer,
            ).paginate(self.game.ctx, location=self.user)
        except self.game.ctx.bot.paginator.NoChoice:
            await self.send(_("You didn't choose anything."))
            return target
        except (discord.Forbidden, discord.HTTPException):
            await self.game.ctx.send(
                _(
                    "I couldn't send a DM to someone. Too bad they missed to use their"
                    " power."
                )
            )
            return target
        if action == 1:
            return target
        target.cursed = True
        self.has_cursed_wolf_father_ability = False
        await self.send(
            _(
                "You have successfully infected **{target}**. They are now **Cursed**"
                " and will join each night in the Werewolves' feast.\n"
            ).format(target=target.user)
        )
        await target.send(
            _(
                "You have been infected by the **{role}**. You will now join in the"
                " Werewolves' nightly killings and feast.\n{game_link}"
            ).format(role=self.role_name, game_link=self.game.game_link)
        )
        if target.role == Role.FLUTIST:
            if target.initial_roles[-1] != target.role:
                target.initial_roles.append(target.role)
            target.role = Role.WEREWOLF
            await target.send(
                _("You became a **{role}** and lost your nocturnal powers.").format(
                    role=target.role_name
                )
            )
            await target.send_information()
        else:
            await target.send(
                _("You still have your powers as **{role}**.").format(
                    role=target.role_name
                )
            )
        return

    @property
    def role_name(self) -> str:
        return self.game.get_role_name(self.role)

    @property
    def own_lovers(self) -> List[Player]:
        own_lovers = []
        for couple in self.game.lovers:
            couple = list(couple)
            if self in couple:
                own_lovers.append(couple[couple.index(self) - 1])
        return own_lovers

    @property
    def in_love(self) -> bool:
        for couple in self.game.lovers:
            if self in couple:
                return True
        return False

    @property
    def dead(self) -> bool:
        return self.lives < 1

    async def kill(self) -> None:
        if self.dead:
            return
        self.lives -= 1
        if self.dead:
            if self.role != self.initial_roles[0] or len(self.initial_roles) > 1:
                if self.exchanged_with_maid:
                    initial_role_info = _(" Initial roles hidden.")
                else:
                    initial_role_info = _(" A **{initial_roles}** initially.").format(
                        initial_roles=", ".join(
                            [
                                self.game.get_role_name(initial_role)
                                for initial_role in self.initial_roles
                            ]
                        )
                    )
            else:
                initial_role_info = ""
            if self.is_sheriff:
                await self.choose_new_sheriff()
            self.game.recent_deaths.append(self)
            # Reveal role in death list
            for p in self.game.players:
                p.revealed_roles.update({self: self.role})
            await self.game.ctx.send(
                _("{user} has died. They were a **{role}**!{initial_role_info}").format(
                    user=self.user.mention,
                    role=self.game.get_role_name(self),
                    initial_role_info=initial_role_info,
                )
            )
            wild_child = discord.utils.find(
                lambda x: x.idol is not None and x.role == Role.WILD_CHILD,
                self.game.alive_players,
            )
            if wild_child and wild_child.idol == self:
                if wild_child.initial_roles[-1] != wild_child.role:
                    wild_child.initial_roles.append(wild_child.role)
                wild_child.role = Role.WEREWOLF

                await wild_child.send(
                    _(
                        "Your idol **{idol}** died, you turned into a"
                        " **{new_role}**.\n{game_link}"
                    ).format(
                        idol=self.user,
                        new_role=wild_child.role_name,
                        game_link=self.game.game_link,
                    )
                )
                await wild_child.send_information()
            additional_deaths = []
            if self.role == Role.HUNTER:
                try:
                    await self.game.ctx.send(_("The Hunter grabs their gun."))
                    target = await self.choose_users(
                        _("Choose someone who shall die with you. 🔫"),
                        list_of_users=[
                            p
                            for p in self.game.alive_players
                            if p not in self.own_lovers
                        ],
                        amount=1,
                        required=False,
                    )
                except asyncio.TimeoutError:
                    await self.game.ctx.send(
                        _("The Hunter couldn't find the trigger 😆.")
                    )
                else:
                    if not target:
                        await self.game.ctx.send(
                            _("The Hunter refused to shoot anyone.")
                        )
                    else:
                        target = target[0]
                        await self.send(
                            _("You chose to shoot **{target}**").format(
                                target=target.user
                            )
                        )
                        await self.game.ctx.send(
                            _("The Hunter is firing. **{target}** got hit!").format(
                                target=target.user
                            )
                        )
                        if target.role == Role.THE_OLD:
                            target.died_from_villagers = True
                            target.lives = 1
                        additional_deaths.append(target)
            elif self.role == Role.KNIGHT:
                if self.attacked_by_the_pact:
                    self.game.rusty_sword_disease_night = 0
                    await self.game.ctx.send(
                        _(
                            "The **{role}** wounded one of the werewolves with their"
                            " Rusty Sword before dying."
                        ).format(role=self.role_name)
                    )
            elif self.role == Role.WAR_VETERAN:
                if self.died_from_villagers:
                    await self.game.ctx.send(
                        _(
                            "The **{role}** was lynched by the Village, a random"
                            " villager was shot."
                        ).format(role=self.role_name)
                    )
                    target = random.choice(
                        [p for p in self.game.alive_players if p not in self.own_lovers]
                    )
                    if target.role == Role.THE_OLD:
                        target.died_from_villagers = True
                        target.lives = 1
                    additional_deaths.append(target)
            elif self.role == Role.THE_OLD and self.died_from_villagers:
                if cursed_one := discord.utils.get(
                    self.game.alive_players, cursed=True
                ):
                    cursed_one.cursed = False  # set temporarily to False
                for p in self.game.alive_players:
                    if p.side not in [Side.WOLVES, Side.WHITE_WOLF]:
                        if p.initial_roles[-1] != p.role:
                            p.initial_roles.append(p.role)
                        if p.role != Role.VILLAGER:
                            p.role = Role.VILLAGER
                if cursed_one:
                    cursed_one.cursed = True  # set it back
                await self.game.ctx.send(
                    _(
                        "The villagers killed **{role}**. The villagers lost all"
                        " their special powers and became normal villagers."
                    ).format(role=self.role_name)
                )
            await self.send(
                _(
                    "💀 You have been eliminated. Please do not communicate with the"
                    " other players until the end of the game.💀\n{game_link}"
                ).format(game_link=self.game.game_link)
            )
            for for_killing in additional_deaths:
                await for_killing.kill()
            if self.in_love and len(self.own_lovers) > 0:
                lovers_to_kill = self.own_lovers
                for lover in lovers_to_kill:
                    if set([self, lover]) in self.game.lovers:
                        self.game.lovers.remove(set([self, lover]))
                    if not lover.dead:
                        await self.game.ctx.send(
                            _(
                                "{dead_player}'s lover, {lover}, will die of sorrow."
                            ).format(
                                dead_player=self.user.mention, lover=lover.user.mention
                            )
                        )
                        if lover.role == Role.THE_OLD:
                            lover.lives = 1
                        await asyncio.sleep(3)
                        await lover.kill()

    @property
    def side(self) -> Side:
        if self.cursed:
            return Side.WOLVES
        if 1 <= self.role.value <= 5:
            return Side.WOLVES
        if 6 <= self.role.value <= 26:
            return Side.VILLAGERS
        else:
            return getattr(Side, self.role.name, "NAN")

    @property
    def has_won(self) -> bool:
        # Returns whether the player has reached their goal or not
        flutist = self.game.get_player_with_role(Role.FLUTIST)
        if (
            flutist
            and self != flutist
            and flutist.has_won
            and flutist in self.own_lovers
        ):
            # For Flutist's lover
            self.game.winning_team = "Flutist"
            return True
        if self.in_love:
            # Special objective for Lovers: The pair must eliminate all other players
            # if one of the lovers is in the Villagers side and the other is in the
            # Wolves or Flutist side.
            # This also checks chain of lovers
            if len(self.game.get_chained_lovers(self)) == len(self.game.alive_players):
                self.game.winning_team = _("Lovers")
                return True
        if self.side == Side.FLUTIST:
            # The win stealer: If the Flutist would win at the same time as another
            # team, the Flutist takes precedence
            if all(
                [
                    p.enchanted or p == self or p in self.own_lovers
                    for p in self.game.alive_players
                ]
            ):
                self.game.winning_team = "Flutist"
                return True
        elif self.side == Side.VILLAGERS:
            if (
                not any(
                    [
                        player.side in (Side.WOLVES, Side.WHITE_WOLF)
                        for player in self.game.alive_players
                    ]
                )
                and self.game.winning_team != "Flutist"
            ):
                self.game.winning_team = "Villagers"
                return True
        elif self.side == Side.WHITE_WOLF:
            if len(self.game.alive_players) == 1 and not self.dead:
                self.game.winning_team = "White Wolf"
                return True
        elif self.side == Side.WOLVES or self.side == Side.WHITE_WOLF:
            if (
                all(
                    [
                        player.side == Side.WOLVES or player.side == Side.WHITE_WOLF
                        for player in self.game.alive_players
                    ]
                )
                and self.game.winning_team != "Flutist"
            ):
                self.game.winning_team = "Werewolves"
                return True
        return False

    async def choose_new_sheriff(self, exclude: Player = None) -> None:
        possible_sheriff = [
            p for p in self.game.alive_players if p != self and p != exclude
        ]
        if not len(possible_sheriff):
            return
        if self.dead:
            await self.send(
                _("You are going to die. Use your last breath to choose a new Sheriff.")
            )
        elif exclude is not None:
            await self.send(
                _(
                    "You exchanged roles with **{dying_user}**. You should choose the"
                    " new Sheriff."
                ).format(dying_user=exclude.user)
            )
        self.is_sheriff = False
        await self.game.ctx.send(
            _("The **Sheriff {sheriff}** should choose their successor.").format(
                sheriff=self.user
            )
        )
        msg = None
        randomize = False
        try:
            sheriff = await self.choose_users(
                _("Choose the new 🎖 Sheriff️."),
                list_of_users=possible_sheriff,
                amount=1,
                required=False,
            )
            if sheriff:
                sheriff = sheriff[0]
            else:
                randomize = True
        except asyncio.TimeoutError:
            randomize = True
        if randomize:
            await self.send(
                _(
                    "You didn't choose anyone. A random player will be chosen to be"
                    " your successor."
                )
            )
            sheriff = random.choice(possible_sheriff)
            msg = _(
                "📢 **{ex_sheriff}** didn't choose anyone. {sheriff} got randomly chosen"
                " to be the new 🎖️ **Sheriff**. **The vote of the Sheriff counts as"
                " double.**"
            ).format(ex_sheriff=self.user, sheriff=sheriff.user.mention)
        sheriff.is_sheriff = True
        await self.send(
            _("**{sheriff}** became the new Sheriff.").format(
                sheriff=sheriff.user.mention
            )
        )
        if not msg:
            msg = _(
                "📢 {sheriff} got chosen to be the new 🎖️ **Sheriff**. **The vote of the"
                " Sheriff counts as double.**"
            ).format(sheriff=sheriff.user.mention)
        await self.game.ctx.send(msg)
        await self.game.dm_sheriff_info()


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
    Role.CURSED_WOLF_FATHER,
]


def get_roles(number_of_players: int, mode: str = None) -> List[Role]:
    number_of_players += 2  # Thief is in play
    roles_to_give = ROLES_FOR_PLAYERS.copy()
    if mode == "Imbalanced":
        roles_to_give = random.shuffle(roles_to_give)
    if mode == "IdleRPG":
        roles_to_give.extend(
            [
                Role.PARAGON,
                Role.RAIDER,
                Role.RITUALIST,
                Role.TROUBLEMAKER,
                Role.LAWYER,
                Role.WAR_VETERAN,
                Role.WOLF_SHAMAN,
                Role.WOLF_NECROMANCER,
            ]
        )
        roles_to_give = random.shuffle(roles_to_give)
    if number_of_players > len(roles_to_give):
        roles = roles_to_give
        # Fill up with villagers and wolves as all special roles are taken
        for i in range(number_of_players - len(roles)):
            if i % 2 == 0:
                roles.append(Role.WEREWOLF)
            else:
                roles.append(Role.VILLAGER)
    else:
        roles = roles_to_give[:number_of_players]
    roles = random.shuffle(roles)
    available_roles = roles[:-2]
    if available_roles.count(Role.SISTER) == 1:
        for idx, role in enumerate(roles):
            if role == Role.SISTER:
                roles[idx] = Role.VILLAGER
    if available_roles.count(Role.BROTHER) < 2:
        for idx, role in enumerate(roles):
            if role == Role.BROTHER:
                roles[idx] = Role.VILLAGER
    return roles


def force_role(game: Game, role_to_force: Role) -> Optional[Role]:
    # Make sure a role is to be played, force it otherwise
    # Warning: This can replace previously forced role
    if role_to_force in game.available_roles:
        return
    else:
        idx = 0  # Let's replace the first role in game.available_roles
        if role_to_force in game.extra_roles:
            # Get it by swapping with game.extra_roles's
            swap_idx = game.extra_roles.index(role_to_force)
            game.available_roles[idx], game.extra_roles[swap_idx] = (
                game.extra_roles[swap_idx],
                game.available_roles[idx],
            )
        else:
            # Or just force it manually
            game.available_roles[idx] = role_to_force
    return random.shuffle(game.available_roles), random.shuffle(game.extra_roles)


if __name__ == "__main__":
    game = Game(50)
    game.run()
